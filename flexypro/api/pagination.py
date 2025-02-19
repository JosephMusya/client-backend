from rest_framework.pagination import PageNumberPagination

class OrdersPagination(PageNumberPagination):
    page_size = 1

class NotificationsPagination(PageNumberPagination):
    page_size = 5
    
class TransactionsPagination(PageNumberPagination):
    page_size = 5

class ChatsPagination(PageNumberPagination):
    page_size = 1000

class SolutionPagination(PageNumberPagination):
    page_size = 1000

class BiddersPagination(PageNumberPagination):
    page_size = 1