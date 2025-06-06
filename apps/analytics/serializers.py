from rest_framework import serializers

class AnalyticsSerializer(serializers.Serializer):
    """
    Basic serializer for analytics data validation
    """
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    
    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Start date must be before end date")
        
        return attrs