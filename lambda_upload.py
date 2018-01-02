
import boto3
from zipfile import ZipFile
import argparse
import json
import os
import shutil

class LambdaMaker(object):
    def __init__(self, config_file, working_dir):
        # const vars
        self.creator='TomLambdaCreator_v1.0.0'
        os.chdir(working_dir)
        self.process_config_file(config_file)

    def process_config_file(self, fname):
        # read config file

        with open(fname, 'r') as f:
          self.contents = json.load(f)
        f.close()
        self.lambda_bucket = self.contents['S3Bucket']
        self.key = self.contents['S3Key']
        self.fname = self.contents['ZipLocalFname']
        self.basename = self.contents['ZipBaseName']
        self.buildDir = self.contents['BuildDir']

        self.functionName=self.contents['FunctionName']
        self.runTime=self.contents['Runtime']
        self.iamRole=self.contents['Role']
        self.handler=self.contents['Handler']
        self.desc=self.contents['Description']
        self.timeout=self.contents['Timeout']
        self.memory=self.contents['MemorySize']
        self.publish=self.contents['Publish']
        self.vpnconfig = {}
        self.vpnconfig['SubnetIds'] = self.contents['SubnetIds']
        self.vpnconfig['SecurityGroupIds'] = self.contents['SecurityGroupIds']
        self.targetArn = self.contents['DeadLetterTargetArn']
        self.env = self.contents['EnvironmentVariables']
        self.tracingConfig = self.contents['TracingConfigMode']
        self.keyarn = self.contents['KeyArn']

    def install_python_dependancies(self):
        deps = self.contents['dependancies']
        for dep in deps:
            cmd = (("pip install {0} -t .").format(dep))
            os.system(cmd)

    def install_node_dependancies(self):

        deps = self.contents['dependancies']
        deplen = len(deps)
        if deplen > 0:
            os.mkdir("node_modules")
            for dep in deps:
                cmd = (("npm install -s {0}").format(dep))
                print(cmd)
                os.system(cmd)

    def make_zip_file(self):
        if (os.path.exists(self.buildDir)):
            # remove old build director
            shutil.rmtree(self.buildDir)

        # make the build dir
        os.mkdir(self.buildDir)

        #copy the source file
        source = self.contents['sourceFile']
        shutil.copy(source, self.buildDir)

        source_files = []
        source_files.append(source)

        os.chdir(self.buildDir)
        if 'node' in self.runTime:
            self.install_node_dependancies()
        else:
            self.install_python_dependancies()

        shutil.make_archive(self.basename, "zip")

        #with ZipFile(self.fname, 'w') as myzip:
        #    for zipit in source_files:
        #        print(("adding {0} to {1}").format(zipit, self.fname))
        #        myzip.write(zipit)

    def push_function_code_to_s3(self):
        self.make_zip_file()
        client = boto3.client('s3')
        response = client.put_object(
            Bucket=self.lambda_bucket,
            Body=open(self.fname, 'rb'),
            Key=self.key)
        metadata=response['ResponseMetadata']
        print(("s3 code metadata = {0}").format(metadata))
        self.s3version = response['VersionId']
        print(('version = {0}').format(self.s3version))

        # now that we pushed the code we can setup the S3
        # info.
        self.setup_function_vars()
        print("pushed code to s3")

    def setup_function_vars(self):
        self.code = {}
        self.code['S3Bucket'] = self.lambda_bucket
        self.code['S3Key'] = self.key
        self.code['S3ObjectVersion'] = self.s3version
        self.desc="Get Location"
        self.deadcfg = {}
        self.deadcfg['TargetArn'] =  self.targetArn
        self.variables = {}
        self.variables['Variables'] = self.env


        self.tracingMode = {}
        self.tracingMode['Mode'] = self.tracingConfig
        # Active needs special permissions
        #self.tracingConfig['Mode'] = 'Active'

        self.tags = {}
        self.tags['FunctionName'] = self.functionName
        self.tags['RunTime'] = self.runTime
        self.tags['Creator'] = self.creator

    def make_new_function(self):
        response = self.lambda_client.create_function(
            FunctionName=self.functionName,
            Runtime=self.runTime,
            Role=self.iamRole,
            Handler=self.handler,
            Code=self.code,
            Description=self.desc,
            Timeout=self.timeout,
            MemorySize=self.memory,
            Publish=self.publish,
            VpcConfig=self.vpnconfig,
            DeadLetterConfig=self.deadcfg,
            Environment=self.variables,
            #KMSKeyArn=self.keyarn,
            TracingConfig=self.tracingMode,
            Tags=self.tags
        )
        print(("lambda create response = {0}").format(response))

    def update_function_code(self):
        response = self.lambda_client.update_function_code(
            FunctionName=self.functionName,
            S3Bucket=self.lambda_bucket,
            S3Key=self.key,
            S3ObjectVersion=self.s3version,
            Publish=True,
            DryRun=False)
        print(("update_function_code response: {0}").format(response))


    def push_code(self):
        self.lambda_client = boto3.client('lambda')
        newFunction = False
        try:
            response = self.lambda_client.get_function(
                                FunctionName=self.functionName)
            #print(response['ResponseMetadata'])
        except Exception:
            newFunction = True

        # push the new code to S3
        self.push_function_code_to_s3()

        if newFunction:
            # new function so make it
            self.make_new_function();
        else:
            # function exists so just update code
            self.update_function_code()

def main():
    parser = argparse.ArgumentParser(description='aws lambda function creator')
    parser.add_argument('-f', required=True, help='json file')
    parser.add_argument('-w', required=True, help='working directory')
    args = parser.parse_args()
    config_file = args.f
    wdir = args.w
    LambdaMaker(config_file).push_code()

if __name__ == "__main__":
  main()
