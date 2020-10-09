# -*- coding: utf-8 -*-
'''
Web Crawler
Author: Luana Bezerra Batista

Date: 10-07-2020

With this Python 3 application, you will be able to extract image URLs from a list of base URLs and from their immediate children 
(i.e., until the second level of websites). It employs the following technologies/libraries, among others:

-> Beautiful Soup, as HTML parser
-> Flask, as a micro web framework
-> concurrent.futures and multiprocessing, for parallel execution

How to run it:

python3 app.py

When the Flask app starts, please open a terminal window in order to run curl commands using the localhost address http://localhost:8080/.

Available curl commands:

# Posting URLs using 1 single task (you need to specify the number of tasks after the localhost address):
curl -X POST http://localhost:8080/1 -H "Content-Type: application/json" -d "[\"http://www.etsmtl.ca/\", \"https://golang.org/\"]"
 
# Posting URLs using 2 paralell tasks (you can use one task per URL):
curl -X POST http://localhost:8080/2 -H "Content-Type: application/json" -d "[\"http://www.etsmtl.ca/\", \"https://golang.org/\"]"
 
# Getting the status of a task:
curl -X GET http://localhost:8080/status/c426926b-64df-4417-8cb8-59f719c41ef1
 
# Getting the result of a task:
curl -X GET http://localhost:8080/result/c426926b-64df-4417-8cb8-59f719c41ef1

#Installing all the dependencies
#!pip install requests bs4 urllib3 futures jsonlib-python3 uuid queuelib flask Flask-UUID
'''

import concurrent.futures
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import os
import json
import uuid
import multiprocessing
import queue
import sys
from flask import Flask, jsonify, make_response, abort, request
from flask_uuid import FlaskUUID


#Flask constructor 
app = Flask(__name__)

#Flask extension that registers a UUID converter for urls on a Flask application
FlaskUUID(app)

#Queue accessible to different workers
q = multiprocessing.Manager().Queue()
pid_dict = {}

#This function extracts image URLs from a list of base URLs and from their
#immediate children (i.e., until the second level of websites)
#It could be improved by allowing the number_of_levels to crawl as parameter. 
def crawl_image_urls(base_url_list, uuid, queue): 

    #setting the pid    
    pid = os.getpid()
    #print("Executing task on process {}".format(pid))       
    queue.put((uuid, pid))    

    #this will store the image urls
    img_url_list = []    

    #extracting all the images found in base_url
    for base_url in base_url_list:       

        resp = requests.get(base_url)

        #using Beautiful Soup as HTML parser
        soup = BeautifulSoup(resp.content, "html.parser")
        
        #extracting all img links from base_url
        BASE_IMAGES = soup.find_all("img")  

        for img in BASE_IMAGES:    
            #making the URL absolute by joining base_url with img_url
            img_url = urljoin(base_url, img.attrs.get("src")) 
            img_url_list.append(img_url)                   

        #getting children_img_urls 
        children_img_urls = crawl_children_image_urls(base_url)
        
        #updating the list with children_img_urls
        img_url_list.append(children_img_urls)

    return (img_url_list)

#Given a base_url, this function finds imediate children websites
#and extracts image URLs from them.
#It returns a list of image URLs.
def crawl_children_image_urls(base_url): 

    #extracting all the URLs found in base_url, that is, it's immediate children
    resp = requests.get(base_url)
    soup = BeautifulSoup(resp.content, "html.parser")
    CHILDREN_URLS = soup.find_all("a")

    #this will store the image urls
    img_url_list = []

    #not employed in this application
    #next_level_url_list = []

    #extracting all the images found in child_url
    for child_url in CHILDREN_URLS:
       
        try:
            url = child_url.get('href') #this request can fail due to MissingSchema
            
            child_resp = requests.get(url)
            
            #making a child soup! :D
            child_soup = BeautifulSoup(child_resp.content, "html.parser")      
            CHILD_IMAGES = child_soup.find_all("img")      

            for img in CHILD_IMAGES:    
                #making the URL absolute by joining base_url with img_url
                img_url = urljoin(url, img.attrs.get("src"))
                img_url_list.append(img_url)   
     
            #getting the next level of websites
            #NEXT_LEVEL_URLS = child_soup.find_all("a")
            #next_level_url_list.append(NEXT_LEVEL_URLS)
           
        except ValueError:
            pass          
       
        #return (img_url_list, next_level_url_list)
        return (img_url_list)

#This function supports max_threads = 1 or max_threads = len(url_list)
#I'm employing the word *thread*, but I'm actually using a ProcessPoolExecutor
#from the library concurrent.futures. 
#A ThreadPoolExecutor is also available in concurrent.futures, however I found 
#ProcessPoolExecutor easier, and I had to make a quick choice.
#When max_threads = len(url_list), it submitts each url to a different task.
#When max_threads = 1, it submitts all urls to the same task.     
#curl -X POST http://localhost:8080/1 -H "Content-Type: application/json"
#--data "[\"http://4chan.org/\", \"https://golang.org/\"]"
@app.route('/<int:max_threads>', methods=['POST'])
def crawl_image_urls_concurrent(max_threads):    
 
    url_list = request.json

    if max_threads > 1:
        n_tasks = len(url_list)
    else:
        n_tasks = 1 

    futures = [] 
    json_dumps = []
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=n_tasks) as executor:
        
        #submitting each url to a different task        
        if n_tasks == len(url_list):
            t = 1;
            for url in url_list:
                u = uuid.uuid4()            
                f = executor.submit(crawl_image_urls, [url], u, q)            
                futures.append(f)   
                pid_dict[u] = [f, None] # PID not known here      
                jd = json.dumps({"job_id": str(u), "task_number": str(t), "url": url})
                print(jd)
                print(f)
                json_dumps.append(jd)
                t = t + 1  

                try:
                    rcv_uuid, rcv_pid = q.get(block=True, timeout=1)
                    pid_dict[rcv_uuid] = [f, rcv_pid] # store PID
                except queue.Empty as e:
                    print('Queue is empty', e)         
        
        #submitting all urls at once (all to the same task)
        elif n_tasks == 1:
            u = uuid.uuid4()                                
            f = executor.submit(crawl_image_urls, url_list, u, q)            
            futures.append(f) 
            pid_dict[u] = [f, None] # PID not known here       
            jd = json.dumps({"job_id": str(u), "task_number": "1", "urls": url_list})
            print(jd)
            print(f)
            json_dumps.append(jd)
            try:
                rcv_uuid, rcv_pid = q.get(block=True, timeout=1)
                pid_dict[rcv_uuid] = [f, rcv_pid] # store PID
            except queue.Empty as e:
                print('Queue is empty', e)  

    return jsonify(json_dumps), 200

#This function outputs the status of a task given it's job_id (uuid). 
#Because of my previous choices,  
#if we've chosen to use thread=1 for crawling multiple URLs, 
#we are unable to see the crawling progress of each URL separately.
#The status is given for the whole process.
#curl -X GET http://localhost:8080/status/0d7fbd8d-2d19-401b-920d-859735c4499a
@app.route('/status/<uuid(strict=False):u>', methods=['GET'])
def get_job_status(u):    
    try: 
        #_uuid_ = uuid.UUID(u) 
        _uuid_ = u      
        [futures, pid] = pid_dict[_uuid_]
        if futures.running():
            jd = json.dumps({"job_id": str(_uuid_), "status": "inprogress"})
            print(jd)
            return jd  
        elif futures.done():
            jd = json.dumps({"job_id": str(_uuid_), "status": "completed"})
            print(jd)
            return jd
        else: 
            jd = json.dumps({"job_id": str(_uuid_), "status": str(futures)})
            print(jd)
            return jd
    except KeyError:
        print('Key not found')      
    except ValueError:
        print('UUID not found')

#Given a job_id (uuid), this function returns it's corresponding crawled image URLs
#curl -X GET http://localhost:8080/result/0d7fbd8d-2d19-401b-920d-859735c4499a
@app.route('/result/<uuid(strict=False):u>', methods=['GET'])
def get_results(u): 
    try: 
        #_uuid_ = uuid.UUID(u) 
        _uuid_ = u      
        [futures, pid] = pid_dict[_uuid_]
        jd = json.dumps({"job_id": str(_uuid_), "result": futures.result()})
        print(jd)
        return jd
    except KeyError:
        print('Key not found')      
    except ValueError:
        print('UUID not found')

#Flask error handlers
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)
@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify({'error': 'Bad Request'}), 400)
@app.errorhandler(500)
def not_found(error):
    return make_response(jsonify({'error': 'Internal Server Error'}), 500)

#Main function
if __name__ == '__main__':    
    app.run(host="0.0.0.0", port=8080) 
    
#Then, open a shell window and run curl commands using the localhost address
#Examples:
#Posting URLs using 1 single task:
#curl -X POST http://localhost:8080/1 -H "Content-Type: application/json" -d "[\"http://4chan.org/\", \"https://golang.org/\"]"
#
#Posting URLs using 2 paralell tasks:
#curl -X POST http://localhost:8080/2 -H "Content-Type: application/json" -d "[\"http://4chan.org/\", \"https://golang.org/\"]"
#
#Getting the status of a task:
#curl -X GET http://localhost:8080/status/c426926b-64df-4417-8cb8-59f719c41ef1
#
#Getting the result of a task:
#curl -X GET http://localhost:8080/result/c426926b-64df-4417-8cb8-59f719c41ef1