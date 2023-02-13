import requests
from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import time,datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import random
import openai

openai.api_key = 'apikeygoeshere'
model_engine = "text-davinci-003"
max_tokens = 2048

filterurl = "https://www.wg-gesucht.de/......" #paste the filter url after setting location, max rent..

def scrape_data():
    req = requests.get(filterurl)
    content = BeautifulSoup(req.content,"html.parser")
    ad_titles = np.array([title.text.strip() for title in content.findAll('h3', {'class': 'truncate_title noprint'})])
    cur_data = np.empty((0,2))
    for i in ad_titles:
        url = content.find('h3', {'class': 'truncate_title noprint','title' : i}).find('a').get('href')
        cur_data = np.vstack((cur_data,np.array([i,url])))
    return pd.DataFrame(cur_data, columns = ['Title','url'])

def send_messages(urls):
    login = 'https://www.wg-gesucht.de/en/mein-wg-gesucht.html' 
    username = "xxxxxx@gmail.com" #enter username and password
    passwd = "xxxxx!"

    driver = webdriver.Chrome('chromedriver.exe') # make sure this file is in path, see any tutorial on how to setup selenium
    driver.get('https://wg-gesucht.de//en/')
    time.sleep(5)

    try:
        driver.find_element_by_id("cmpbntyestxt").click() # Accept cookies
    except : print("Error accepting cookies")

    driver.get(login) # login page
    time.sleep(1)
    driver.find_element_by_id("login_email_username").send_keys(username)
    driver.find_element_by_id("login_password").send_keys(passwd)
    driver.find_element_by_id("auto_login").click()
    driver.find_element_by_id("login_submit").click()
    time.sleep(3)
    
    for url in urls:
        try: #Check for a WG leben section
            lebenurl = requests.get('https://www.wg-gesucht.de/' + url[1:])
            contentl = BeautifulSoup(lebenurl.content,"html.parser")
            description = str(contentl.find('p', {'class': 'freitext', 'id': 'freitext_2_content'}))[55:] 
        except:
            print('Ad has no WG Leben section')
            description = ''

        try:
            
            driver.get('https://www.wg-gesucht.de/nachricht-senden/' + url[1:]) #go to ad
        except:
            print("Ad has no message option")
            continue
        time.sleep(1)

        try: #incase there is a security confirmation
            driver.find_element_by_id("sicherheit_bestaetigung").click()
        except:
            pass
        
        if description == '' :

            driver.find_element_by_id("message_input").send_keys(message) #write message
            
        else :
            prompt = "This is an advert for a room:" + description + "I am Max a 24 year old student.
				Write a friendly and chill message in German to get a room here. 
				Make sure to find something in common with people living there."

            completion = openai.Completion.create(engine=model_engine,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.5,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0)

            driver.find_element_by_id("message_input").send_keys(completion.choices[0].text) #write message with ChatGPT
            print(completion.choices[0].text)
                                            
        try:
            
            driver.find_element_by_xpath("//button[@type='submit']").click() #SEND
            print("New message sent!")
            break
        
        except : 
            pass

    driver.close()

history = pd.read_csv('written_ads.csv')
previous_data = scrape_data().drop_duplicates()


while True:
    
    print("Last scan: ",  datetime.datetime.now())
    time.sleep(120) # Scans every 120 seconds
    new_data = scrape_data().drop_duplicates()
    diff = pd.concat([new_data,previous_data]).drop_duplicates(keep=False)
    duplicate = False
    diff = diff[diff.Title != "(Verfügbar 1-24 Monate) - Liebevolles Apartment, verkehrsgünstige Lage, 500 m S-Bahn, Süd Balkon, Parkplatz, löffelfertig" ] 
    #a stupid sponsered ad that comes up all the time, removing..
    if diff.size>0 : 
        print("New Ad posted") # New listing
        
        for i in history.iloc[:,0]: #Checking for duplicates
            for j in diff.iloc[:,0]:

                if i == j:
                    print("Identified as duplicate")
                    duplicate = True
        
        ads = list(diff.iloc[:,1])

        if not duplicate:
            
            send_messages(ads)
            df = diff.iloc[:,:2]
            df.to_csv('written_ads.csv', mode='a', index=False, header=False) #Keeps track of responded ads to avoid double texting
    
    
    previous_data = new_data    
    
    
