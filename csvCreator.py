import csv,os

file = 'rootList.csv'



with open(file,'w') as file:
    write = csv.writer(file,lineterminator='\n')
    for filename in os.listdir("C:\\Users\\Jonathan\\Desktop\\Kivy Media Center\\Songs"):
        write.writerow([filename])
    file.close()
