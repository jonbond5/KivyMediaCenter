from tempfile import NamedTemporaryFile
import shutil
from csv import reader, writer
##
filename = 'playlist1.csv'
tempfile = NamedTemporaryFile(delete=False,dir='C:\\Users\Jonathan\\Desktop\\Kivy Media Center')


##with open('playlist1.csv','a+') as file,tempfile:
##    w = csv.reader(file,delimiter='\n')
##    r = csv.writer(tempfile,delimiter='\n')
##    for row in file:
##        print(row)
##        r.writerow([row+'234'])
##with open(tempfile.name,'r') as file:
##    print(2)
##    for row in file:
##        print(1)
##        print(row)
##shutil.move(tempfile.name,filename)

with open('playlist1.csv','r+') as file:
    with open(tempfile.name,'w+') as tempfile:
        w = writer(tempfile,lineterminator='\n')
        
        for row in file:
            w.writerow([row[:-1]+'234'])
            
shutil.move(tempfile.name,filename)
