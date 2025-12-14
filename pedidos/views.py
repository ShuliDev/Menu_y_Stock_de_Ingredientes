from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Pedido
from .serializers import PedidoSerializer


class PedidoViewSet(ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        pedido = self.get_object()
        try:
            from django.core.exceptions import ValidationError
            try:
                from mainApp.views import StockService
            except Exception:
                StockService = None
            # validar y reservar stock: suponemos cantidad 1
            if StockService:
                svc = StockService()
                try:
                    svc.validar_y_reservar_stock(int(pedido.plato), 1, str(pedido.id))
                except ValidationError as e:
                    return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            pedido.confirmar()
            serializer = self.get_serializer(pedido)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        pedido = self.get_object()
        try:
            pedido.cancelar()
            serializer = self.get_serializer(pedido)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["patch"])
    def listo(self, request, pk=None):
        pedido = self.get_object()
        try:
            pedido.marcar_listo()
            serializer = self.get_serializer(pedido)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["patch"])
    def entregar(self, request, pk=None):
        pedido = self.get_object()
        try:
            pedido.entregar()
            serializer = self.get_serializer(pedido)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["patch"])
    def cerrar(self, request, pk=None):
        pedido = self.get_object()
        try:
            pedido.cerrar()
            serializer = self.get_serializer(pedido)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def cocina_estado(request):
    pid = request.data.get("pedido_id")
    estado = request.data.get("estado")
    if not pid or not estado:
        return Response(
            {"detail": "pedido_id y estado son requeridos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        p = Pedido.objects.get(pk=pid)
        if estado == "EN_PREPARACION":
            if p.estado != Pedido.Estado.CREADO:
                return Response(
                    {"detail": "Solo desde CREADO."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            p.estado = Pedido.Estado.EN_PREPARACION
            p.full_clean()
            p.save(update_fields=["estado", "actualizado_en"])
        elif estado == "LISTO":
            p.marcar_listo()
        elif estado == "CANCELADO":
            p.cancelar()
        else:
            return Response({"detail": "Estado inválido."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PedidoSerializer(p).data)
    except Pedido.DoesNotExist:
        return Response({"detail": "Pedido no existe."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def cocina_list(request):
    activos = Pedido.objects.exclude(
        estado__in=[Pedido.Estado.CANCELADO, Pedido.Estado.CERRADO]
    ).order_by("creado_en")
    return Response(PedidoSerializer(activos, many=True).data)
