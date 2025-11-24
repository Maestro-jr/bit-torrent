#import sys
import grpc
from concurrent import futures
import calculator_pb2
import calculator_pb2_grpc


class job :
    def __init__(self, operator, operand1, operand2) -> None:
        self.__operator = operator
        self.__operand1 = int(operand1)
        self.__operand2 = int(operand2)
    def operator(self) -> str:
        return self.__operator
    def operand1(self) -> int:
        return self.__operand1
    def operand2(self) -> int:
        return self.__operand2

def run(operator, num1, num2):
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = calculator_pb2_grpc.CalculatorStub(channel)
        if (operator == "add"):
            response = stub.Add(calculator_pb2.AddRequest(num1=num1, num2=num2))
        elif (operator == "sub"):
            response = stub.Sub(calculator_pb2.AddRequest(num1=num1, num2=num2))
        elif (operator == "mul"):
            response = stub.Mul(calculator_pb2.AddRequest(num1=num1, num2=num2))
        elif (operator == "div"):
            response = stub.Div(calculator_pb2.AddRequest(num1=num1, num2=num2))
        elif (operator == "mod"):
            response = stub.Mod(calculator_pb2.AddRequest(num1=num1, num2=num2))
        else:
            print("Invalid operator")
            exit()
    print(f"Result: {response.result}")

# if __name__ == '__main__':
#     # Get user Input 
#     operand = sys.argv[1]
#     num1 = sys.argv[2]
#     num2 = sys.argv[3]
#     # print(f"operand = {operand},  num1 = {num1}, num2 = {num2}")
#     run(operand, num1, num2)

if __name__ == '__main__':
    # threads created to handle concurrent requests
    workers = futures.ThreadPoolExecutor(max_workers=10)
    # list of jobs that will be submitted on the cloud
    jobs = [job("add", "633", "27"),
            job("sub", "633", "27"), 
            job("div", "633", "27"),
            job("mod", "633", "27"),] 
    # Get user Input
    for job in jobs:
        workers.submit(run, job.operator(), job.operand1(), job.operand2())