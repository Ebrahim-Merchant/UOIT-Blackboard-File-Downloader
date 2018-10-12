import requests
from bs4 import BeautifulSoup
import json
from pprint import pprint
import os
import datetime
import shutil
import getpass
import re

login_session = requests.Session()
username = ""

# Input: username and password for uoit.blackboard.com
# Creates a log in session for uoit.blackboard.com
def login(usrname, password):
    global login_session
    global username
    username = usrname
    URL = "https://login.uoit.ca/cas/login?service=https%3A%2F%2Fuoit.blackboard.com%2Fwebapps%2Fbb-auth-provider-cas-BBLEARN%2Fexecute%2FcasLogin%3Fcmd%3Dlogin%26authProviderId%3D_123_1%26redirectUrl%3Dhttps%253A%252F%252Fuoit.blackboard.com%252Fwebapps%252Fportal%252Fexecute%252FdefaultTab%26globalLogoutEnabled%3Dtrue"
    login_page=login_session.get(URL)
    soup = BeautifulSoup(login_page.text, 'html.parser')
    hidden_keys = []
    for hidden in soup.find_all('input', {'type':'hidden'}):
        hidden_keys.append(hidden.get('value'))
    LT = hidden_keys[0]
    EXECUTION = hidden_keys[1]
    login_data = {
        'username':username,
        'password':password,
        'lt': LT,
        'execution': EXECUTION,
        '_eventId':'submit',
        'submit':'LOGIN'
    }
    headers = {
        'referer':URL
    }
    r = login_session.post(URL, data=login_data, headers= headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    if len(soup.findAll('div',{'class':'errors'}))> 0:
           return False
    else:
           return True

        
def fixName(old_name):
    new_name = re.sub('[^a-zA-Z0-9-&, \n\.]', ' ', old_name)
    return new_name


    
def getCoursesList(baseDir,year, month):
    global login_session
    global username
    courses = []
    data = login_session.get('https://uoit.blackboard.com/learn/api/public/v1/users/userName:'+username+'/courses')
    if data.status_code == 404:
         print("There was a error logging in. Please try again")
         return
    soup = BeautifulSoup(data.text, 'html.parser')
    parsed_courses = json.loads(soup.text)
    try:
        for course in parsed_courses["results"]:
            courseString = course["created"]
            date = courseString.split("T")[0]        
            course_creation_date = datetime.datetime.strptime(date,'%Y-%m-%d')
            if course_creation_date.year >= int(year) and course_creation_date.month >= int(month):
                courseId = course['courseId']
                data = login_session.get('https://uoit.blackboard.com/learn/api/public/v1/courses/'+courseId)
                json_data =json.loads(data.text)
                courses.append(json_data)
    except KeyError:
        return "Cannot get courses"
    f = open(baseDir+'\\courses.json','w')
    f.write(json.dumps(courses))
    f.close()



def getCourse(baseDir):
    global login_session
    f = open(baseDir+'\\courses.json','r')
    courses = json.loads(f.read())
    f.close()
    for course in courses:
        courseId = course["id"]
        folderName = fixName(course["description"])
        print("Getting "+folderName+" files")
        newDir = baseDir+"\\"+folderName
        if not os.path.exists(newDir):
            try:
                os.mkdir(newDir)
            except OSError as e:
                print(folderName+" was not created")
                break
        response = login_session.get('https://uoit.blackboard.com/learn/api/public/v1/courses/'+courseId+'/contents')
        if response.status_code is 200:
            json_data = json.loads(response.text)
            for data in json_data['results']:
                downloadFiles(courseId, newDir, data)


def downloadFiles(courseId, baseDir, folder):
    if "hasChildren" in folder:
        folderName = fixName(folder['title'])
        newDir = baseDir + "\\"+ folderName
        if not os.path.exists(newDir):
            try:
                os.mkdir(newDir)
            except NotADirectoryError as e:
                print(folderName+" was not created")                               
        data = login_session.get('https://uoit.blackboard.com/learn/api/public/v1/courses/'+courseId+'/contents/'+folder['id']+'/children')
        json_data = json.loads(data.text)
        if data.status_code is 200:
            for data in json_data['results']:            
                downloadFiles(courseId, newDir, data)
    else:
        data = login_session.get('https://uoit.blackboard.com/learn/api/public/v1/courses/'+courseId+'/contents/'+folder['id']+'/attachments')
        json_data = json.loads(data.text)
        if data.status_code == 200 and len(json_data['results'])>0:
            for data_new in json_data['results']:
                    download_url = 'https://uoit.blackboard.com/learn/api/public/v1/courses/'+courseId+'/contents/'+folder['id']+'/attachments/'+data_new['id']+'/download'
                    file = login_session.get(download_url,stream = True)
                    fileName = fixName(data_new['fileName'])
                    output_file = baseDir+"\\"+fileName
                    if not os.path.exists(output_file):
                        with open(output_file, 'wb') as out_file:
                            shutil.copyfileobj(file.raw, out_file)
                        del file
        elif "body" in folder:
            fileName = fixName(folder['title'])
            file = open(baseDir+"\\"+fileName+'.html', 'w', encoding="utf-8")
            file.write(folder['body'])
            file.close()

                                     
    

def main():    
        print("Enter your username:")
        user = input()
        password = getpass.getpass("[%s's password] " % user)
        if login(user, password):
            print("Authentication has been successful\n")
            print("Enter the directory you want to save the files and folders in\n")
            directory = input()
            print("Starting with which semester do you want to download the courses? e.g Fall 2018\nThe program will download all the course files from Fall 2018 onwards\n")
            semester = input()
            semester = semester.split(" ")
            if semester[0] == "Fall":
                semester[0] = 7
                semester[1] = int(semester[1])
            elif semester[0] == "Winter":
                semester[0] = 10
                semester[1] = int(semester[0]) - 1

            getCoursesList(directory, semester[1], semester[0])
            getCourse(directory)
        else:
            print("The username and password combination was incorrect")

    
if __name__ == "__main__":
    main()
