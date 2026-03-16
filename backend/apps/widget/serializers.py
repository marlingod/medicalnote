from rest_framework import serializers


class WidgetConfigSerializer(serializers.Serializer):
    logo_url = serializers.URLField(required=False, default="")
    brand_color = serializers.CharField(required=False, default="#000000")
    custom_domain = serializers.CharField(required=False, default="")
    practice_name = serializers.CharField(read_only=True)
