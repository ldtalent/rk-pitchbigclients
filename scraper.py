import re
import glob
import datetime
import json
import csv 
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
from time import sleep

#scrape skills from LD
def getskills():
    driver = webdriver.Chrome()
    mainurl = 'https://www.learningdollars.com/client/select_engineers/'
    driver.get(mainurl)   
    categorylist=driver.find_elements_by_xpath('/html/body/div[2]/div[3]/div[2]/form/div[1]/div[1]/div/select/option')
    category = []
    skills = []
    for item in categorylist[1:]:
        category.append(item.text)
        skillslist = []
        item.click()
        skillslist=driver.find_elements_by_xpath('/html/body/div[2]/div[3]/div[2]/form/div[1]/div[2]/div/select/option')
        skills.append([i.text for i in skillslist])        
    driver.close()
    categoryskill = {}
    count = 0
    for i in category:
        if count == 0:
            categoryskill[i] = sorted(skills[count])
        else:
            skillcurrent = set(skills[count])
            skillprevious = set(skills[count - 1])
            skillfinal = skillcurrent-skillprevious
            categoryskill[i] = sorted(list(skillfinal))
        count = count + 1
    return categoryskill

#Function to get link
def getlink(skilllist):
    driver = webdriver.Chrome()
    mainurl = 'https://www.learningdollars.com/client/select_engineers/'
    driver.get(mainurl)   
    categorylist=driver.find_elements_by_xpath('/html/body/div[2]/div[3]/div[2]/form/div[1]/div[1]/div/select/option')
    #Different bottons
    selectbotton = driver.find_element_by_xpath('//*[@id="move-right"]')
    findengs = driver.find_element_by_xpath('/html/body/div[2]/div[3]/div[2]/form/button[1]')
    #Selecting category
    categorylist[0].click()    
    skills=driver.find_elements_by_xpath('/html/body/div[2]/div[3]/div[2]/form/div[1]/div[2]/div/select/option')
    for skill in skills:
        if str(skill.text) in skilllist:
            skill.click()
            selectbotton.click()
    findengs.click()
    getlink = driver.find_element_by_xpath('//*[@id="shareable_link_btn"]')
    getlink.click()
    sleep(5)
    link = driver.find_element_by_xpath('//*[@id="shareable_link_text"]').text
    sleep(5)
    driver.close()
    return link

#main function with all the functionality
def scrape(filename,driver,jobs,mode):
    #Getting skills to compare    
    ldskills = getskills()
    ldcategory = [*ldskills]
    allskills = []
    for category in ldcategory:
        allskills.extend(ldskills[category])
    #Setting writing modes
    if mode == 1:
        filemode = 'a'
    else:
        filemode = 'w'
    #Sorting data for append mode
    if filemode == 'a':
        df = pd.read_csv(filename, encoding = "ISO-8859-1")
        df['Datetime'] = pd.to_datetime(df.Datetime, infer_datetime_format = True)
        df.sort_values(by = 'Datetime', ascending = False, inplace = True) 

    with open(filename, filemode, newline='',  encoding="utf-8") as file:
        writer = csv.writer(file)
        if filemode == 'w':
            writer.writerow(["Datetime", "Name", "Job_title","Skills","Description","Engineers_link"])            
        #Extracting data    
        for i in jobs:
            skill = []
            job = BeautifulSoup(i.get_attribute("innerHTML"), features = "lxml")
            companyjob = job.find(class_ ="company position company_and_position")
            companyname = companyjob.find("h3").text
            companytitle = companyjob.find("h2").text
            tags = job.find(class_ = "tags").find_all(class_=re.compile("^tag"))
            for tag in tags:
                tagname = str(tag.find('h3').text).title()
                #Condition to check if the skill exist in the job descriptionq
                if tagname in allskills:
                    skill.append(tagname)
                else:
                    continue

            time = job.find("time")['datetime']            
            time = datetime.datetime.strptime(''.join(time.rsplit(':', 1)), '%Y-%m-%dT%H:%M:%S%z')
            #Extract Description
            clickBot = i.find_elements_by_tag_name("td")[1]
            driver.execute_script("arguments[0].click();", clickBot)
            allrows = driver.find_elements_by_tag_name("tr")
            try:        
                description = [x for x in allrows if 'active' in x.get_attribute('class')][0]
                description= BeautifulSoup(description.get_attribute("innerHTML"), features = "lxml").text
                deslength= len(description)
                while True:
                    deslength-=1 
                    if description[deslength] == "}":
                        break
                    if deslength == 0:
                        break
                descriptionfinal = json.loads(description[:deslength+1])
            except:
                print("Description not found")
                descriptionfinal = dict()
                descriptionfinal['description'] = "Not Found"
            driver.execute_script("arguments[0].click();", clickBot)

            #Extracting skill from description
            for allskill in allskills:
                if allskill.lower() in str(descriptionfinal['description']).lower():
                    if (len(allskill)>3):
                        skill.append(allskill)          

            if filemode == 'w':
                if len(skill)>3:
                    link = getlink(skill)
                    writer.writerow([time,companyname, companytitle, skill, descriptionfinal['description'], link])
                    print("Added new job: ", companytitle )
            else:
                if (time <= df['Datetime'][0]):
                    break
                else:
                    if len(skill)>=1:
                        link = getlink(skill)
                        writer.writerow([time,companyname, companytitle, skill, descriptionfinal['description'], link])
                        print("Added new job: ", companytitle )
    

def scrapemode(file, mode):
    mainurl= "https://remoteok.io/remote-dev-jobs"
    driver = webdriver.Chrome()
    driver.get(mainurl)  
    jobs = driver.find_elements_by_tag_name("tr")
    jobs = [x for x in jobs if "job-" in x.get_attribute('id')]
    scrape(file,driver,jobs,mode)
    if mode == 1:
        df_new = pd.read_csv(file, encoding = "ISO-8859-1")
        df_new['Datetime'] = pd.to_datetime(df_new.Datetime, infer_datetime_format = True)
        df_new.sort_values(by = 'Datetime', ascending = False, inplace = True)
        today = datetime.datetime.now()
        newfilename = 'remote_jobs_' + str(today.year)+ '_'+ str(today.month)+'_'+str(today.day) +'.csv'
        df_new.to_csv(newfilename, index=False)
    driver.close()
    
            
def main():
    print("Enter 1 if you want to provide existing csv.")
    print("Enter 2 if you want to create a new csv.")
    choice = 0
    while True:
        while True:
            try:
                choice = int(input("Your Choice: "))
                break
            except:
                print("Invalid input. Please enter a number")
        if choice == 1:
            files = list(glob.glob("*.csv"))
            count = 1
            for file in files:
                print("Enter ", count, " to select ", file)
                count+=1
            if len(files) <= 0:
                print("CSV file not found. Please add csv file to the working directory")
                break
            while True:
                try:         
                    choice = int(input("Your choice: "))
                except:
                    print("Invalid input. Please enter a number")
                    continue
                if (choice < 1) or (choice > count):
                    print("Invalid input. Please select a number between 1 and ", count)
                else:
                    break            
            filename = files[choice-1]
            scrapemode(str(filename),1)
            break

        elif choice == 2:
            today = datetime.datetime.now()
            filename = 'remote_jobs_' + str(today.year)+ '_'+ str(today.month)+'_'+str(today.day) +'.csv'
            scrapemode(filename, 2)
            break
  

if __name__ == "__main__":
    main()