from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import RealizedProfit
from .serializers import RealizedProfitSerializer

class RealizedProfitAPIView(APIView):
    def get(self, request, *args, **kwargs):
        user = self.request.user
        try:
            realized_profit, created = RealizedProfit.objects.get_or_create(user=user)
            realized_profit.update_realized_profit()
            realized_profit.save()
            serializer = RealizedProfitSerializer(realized_profit)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except RealizedProfit.DoesNotExist:
            return Response({'detail': 'RealizedProfit data not found.'}, status=status.HTTP_404_NOT_FOUND)
