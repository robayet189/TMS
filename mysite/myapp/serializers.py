# Import Django REST Framework serializers for API data serialization
from rest_framework import serializers
from .models import Bus, BusLocation

class BusSerializer(serializers.ModelSerializer):
    """
    Serializer for Bus model - CHANGE REASON: Convert Bus objects to JSON for API responses
    Defines which fields to include in API responses for bus data
    """
    class Meta:
        model = Bus
        fields = ['id', 'bus_number', 'capacity', 'has_ac', 'current_lat', 'current_lng']


class BusLocationSerializer(serializers.ModelSerializer):
    """
    Serializer for BusLocation model - CHANGE REASON: Convert location data to JSON for tracking API
    Includes related bus number for frontend display convenience
    """
    # Read-only field to include bus number from related Bus model
    bus_number = serializers.CharField(source='bus.bus_number', read_only=True)
    
    class Meta:
        model = BusLocation
        fields = ['id', 'bus', 'bus_number', 'latitude', 'longitude', 'updated_at']