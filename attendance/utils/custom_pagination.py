from rest_framework import pagination 
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from mms import serializers
from rest_framework import  status

class CustomPagination(PageNumberPagination):
    page_size = 1  # Change this value according to your preference
    page_size_query_param = 'page_size'
    max_page_size = 1
    page_query_param = 'page'

    # def get_paginated_response(self, data):
    #     return Response({
    #         'next': self.get_next_link(),
    #         'previous': self.get_previous_link(),
    #         'count': self.page.paginator.count,
    #         'total_pages': self.page.paginator.num_pages,
    #         'results': data
    #     })
    
    # def paginate_queryset(self, queryset, request, view=None):
    #     self.page = self.paginate_queryset(queryset, request, view=view)
    #     if self.page is not None:
    #         serializer = serializers.FetchQuoteSerializer(self.page, many=True, context={"user_id": request.user.id})
    #         return self.get_paginated_response(serializer.data)
    #     else:
    #         serializer = serializers.FetchQuoteSerializer(queryset, many=True, context={"user_id": request.user.id}).data
    #         return Response(serializer, status=status.HTTP_200_OK)

# class CustomPagination(pagination.PageNumberPagination):
#     def get_paginated_response(self, data):
#         return Response({
#             'links': {
#                 'next': self.get_next_link(),
#                 'previous': self.get_previous_link()
#             },
#             'count': self.page.paginator.count,
#             'results': data
#         })