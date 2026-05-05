from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class TransactionPagination(PageNumberPagination):
    """
    Paginates the transaction list endpoint.

    Query params:
        ?page=2          → page number (default: 1)
        ?page_size=20    → items per page (default: 20, max: 100)

    Response shape:
        {
            "count":    142,        // total matching transactions
            "next":     "http://.../?page=3",
            "previous": "http://.../?page=1",
            "pages":    8,          // total pages
            "results":  [...]       // transactions for this page
        }
    """
    page_size              = 20
    page_size_query_param  = 'page_size'
    max_page_size          = 100
    page_query_param       = 'page'

    def get_paginated_response(self, data):
        return Response({
            'count':    self.page.paginator.count,
            'next':     self.get_next_link(),
            'previous': self.get_previous_link(),
            'pages':    self.page.paginator.num_pages,
            'results':  data,
        })