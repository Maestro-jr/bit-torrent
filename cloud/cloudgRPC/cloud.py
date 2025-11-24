import grpc
from concurrent import futures
import calculator_pb2
import calculator_pb2_grpc

class CalculatorSkeleton(calculator_pb2_grpc.CalculatorServicer):
    def Add(self, request, context):
        result = request.num1 + request.num2
        return calculator_pb2.AddResponse(result=result)
    def Sub(self, request, context):
        result = request.num1 - request.num2
        return calculator_pb2.AddResponse(result=result)
    def Mul(self, request, context):
        result = request.num1 * request.num2
        return calculator_pb2.AddResponse(result=result)
    def Div(self, request, context):
        result = request.num1 // request.num2
        return calculator_pb2.AddResponse(result=result)
    def Mod(self, request, context):
        result = request.num1 % request.num2
        return calculator_pb2.AddResponse(result=result)

def run():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    calculator_pb2_grpc.add_CalculatorServicer_to_server(CalculatorSkeleton(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    run()