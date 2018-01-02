lambda_upload

Python 3 utility script that will create or update a node or python lamda function.

Contents:
 - lambda_upload.py:
   -f config file
   -d working directory that contains the lambda source code file.


Config Vars:

  The example config file maps to the AWS lambda values with a couple exceptions
     - ZipBaseName/ZipFileName
       location of the zip file to upload to S3 with and without .zip prefix
       (todo: remove ZipFileName)
     - SourceFile source file for the lambda funcion. Should be relative to working directory
     - BuildDir this is where the sourcefile and dependancies are copied to make the zip file. I would suggest ./build
     - dependancies
       for Node these are the things you would go npm install foo and for python these are the names of pip packages. 