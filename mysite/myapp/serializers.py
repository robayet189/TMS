from rest_framework import serializers
from .models import Bus, BusLocation

class BusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = ['id', 'bus_number', 'capacity', 'has_ac', 'current_lat', 'current_lng']


class BusLocationSerializer(serializers.ModelSerializer):
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    
    class Meta:
        model = BusLocation
        fields = ['id', 'bus', 'bus_number', 'latitude', 'longitude', 'updated_at']