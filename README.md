# Web Crawler

Author: Luana Bezerra Batista

Date: 10-07-2020

With this Python application, you will be able to extract image URLs from a list of base URLs and from their immediate children 
(i.e., until the second level of websites). It employs the following technologies/libraries, among others:

* Beautiful Soup, as HTML parser

* Flask, as a micro web framework

* concurrent.futures and multiprocessing, for parallel execution

############################################################################
# How to run it:

`git clone https://github.com/luana-be/crawler-test.git`

`cd crawler-test`

`docker build -t crawler-test -f Dockerfile ./`

`docker run -p 8080:8080 crawler-test`

############################################################################

When the Flask app starts, please open another terminal window in order to run curl commands using the address http://localhost:8080/

Available curl commands:

# Posting URLs using 1 single task 
*Note that you need to specify the number of tasks after the localhost address

`curl -X POST http://localhost:8080/1 -H "Content-Type: application/json" -d "[\"http://www.etsmtl.ca/\", \"https://golang.org/\"]"`
 
# Posting URLs using 2 paralell tasks:
*Note that you can use one task per URL

`curl -X POST http://localhost:8080/2 -H "Content-Type: application/json" -d "[\"http://www.etsmtl.ca/\", \"https://golang.org/\"]"`
 
# Getting the status of a task:

`curl -X GET http://localhost:8080/status/c426926b-64df-4417-8cb8-59f719c41ef1`
 
# Getting the result of a task:

`curl -X GET http://localhost:8080/result/c426926b-64df-4417-8cb8-59f719c41ef1`
