## Build the container 

docker build -t sample_ant .

## Creating a dynamodb table for testing purpose

#### Note DDB table creation  needs to happen before running either container
aws dynamodb create-table --region us-west-2 --table-name ABCTable --attribute-definitions AttributeName=EndpointName,AttributeType=S --key-schema AttributeName=EndpointName,KeyType=HASH  --billing-mode PAY_PER_REQUEST

## Run locally 

docker run -p 8080:8080 -e ROUTING_TABLE_NAME=ABCTable -e ROUTING_ENTRY_KEY=xyzEp  -e AWS_ACCESS_KEY_ID=<your-key> -e AWS_SECRET_ACCESS_KEY=<your-secret> sample_ant 

## Test invoke 

curl -X POST localhost:8080/invocations

you should see something like 
```
Starting testing on port 5001
Starting testing on port 5002
Starting testing on port 5003
Starting testing on port 5004
Starting testing on port 5005
Starting iperf3 client run on port 5001
Megabits per second  (Mbps)  9636.109 for client port 5001
Starting iperf3 client run on port 5002
Megabits per second  (Mbps)  9536.848 for client port 5002
Starting iperf3 client run on port 5004
Megabits per second  (Mbps)  10053.12 for client port 5004
Starting iperf3 client run on port 5003
Megabits per second  (Mbps)  10128.15 for client port 5003
Starting iperf3 client run on port 5005
Megabits per second  (Mbps)  10174.74 for client port 5005
```
