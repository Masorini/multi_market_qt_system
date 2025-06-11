from core.order import Order
from execution.gateway import ExecutionGateway

class ExecutionEngine:
    def __init__(self, gateway: ExecutionGateway):
        self.gateway = gateway

    def submit_order(self, order: Order):
        result = self.gateway.send_order(order)
        return result