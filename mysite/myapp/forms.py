from django import forms
from .models import Bus, Route, Schedule, Driver, VehicleIssue

class BusForm(forms.ModelForm):
    """
    Form for adding/editing Bus records
    CHANGE REASON: Provide validated form fields for admin bus management
    """
    class Meta:
        model = Bus
        fields = ['bus_number', 'capacity', 'driver_name', 'driver_phone', 'has_ac', 'has_wifi', 'is_active']
        widgets = {
            'bus_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., BUS-001'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': '10', 'max': '100'}),
            'driver_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Driver full name'}),
            'driver_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+880 1XXXXXXXXX'}),
            'has_ac': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_wifi': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_bus_number(self):
        """Validate bus number format - CHANGE REASON: Ensure consistent bus numbering"""
        bus_number = self.cleaned_data.get('bus_number')
        if bus_number and not bus_number.strip():
            raise forms.ValidationError("Bus number cannot be empty")
        return bus_number.strip().upper()
    
    def clean_capacity(self):
        """Validate capacity range - CHANGE REASON: Prevent invalid seat counts"""
        capacity = self.cleaned_data.get('capacity')
        if capacity and (capacity < 10 or capacity > 100):
            raise forms.ValidationError("Capacity must be between 10 and 100 seats")
        return capacity


class RouteForm(forms.ModelForm):
    """
    Form for adding/editing Route records
    CHANGE REASON: Provide validated form fields for admin route management
    """
    class Meta:
        model = Route
        fields = ['code', 'start', 'end', 'distance_km']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., R-01', 'maxlength': '10'}),
            'start': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Starting point'}),
            'end': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ending point'}),
            'distance_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'e.g., 18.4'}),
        }
    
    def clean_code(self):
        """Validate route code format - CHANGE REASON: Ensure unique route codes"""
        code = self.cleaned_data.get('code')
        if code:
            code = code.strip().upper()
            if not code:
                raise forms.ValidationError("Route code cannot be empty")
        return code
    
    def clean(self):
        """Validate start and end are different - CHANGE REASON: Prevent circular routes"""
        cleaned_data = super().clean()
        start = cleaned_data.get('start')
        end = cleaned_data.get('end')
        if start and end and start.lower() == end.lower():
            raise forms.ValidationError("Start and end locations cannot be the same")
        return cleaned_data


class ScheduleForm(forms.ModelForm):
    """
    Form for adding/editing Schedule records
    CHANGE REASON: Provide validated form fields with proper bus/route queryset for dropdowns
    """
    # CHANGE: Use ModelChoiceField with filtered queryset for bus dropdown
    bus = forms.ModelChoiceField(
        queryset=Bus.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select a Bus",
        required=True
    )
    # CHANGE: Use ModelChoiceField with filtered queryset for route dropdown
    route = forms.ModelChoiceField(
        queryset=Route.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select a Route",
        required=True
    )
    
    class Meta:
        model = Schedule
        fields = ['route', 'bus', 'departure_time', 'arrival_time', 'travel_date', 'fare', 'available_seats', 'is_active']
        widgets = {
            'departure_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'arrival_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'travel_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fare': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'available_seats': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        """
        Initialize form with filtered bus queryset
        CHANGE REASON: Only show active buses in dropdown to prevent scheduling inactive buses
        """
        super().__init__(*args, **kwargs)
        # CHANGE: Filter bus queryset to only active buses
        self.fields['bus'].queryset = Bus.objects.filter(is_active=True)
        # If editing an existing schedule, ensure the assigned bus is included even if inactive
        if self.instance.pk and self.instance.bus and not self.instance.bus.is_active:
            self.fields['bus'].queryset = Bus.objects.filter(
                models.Q(is_active=True) | models.Q(id=self.instance.bus.id)
            )
    
    def clean(self):
        """Validate schedule logic - CHANGE REASON: Ensure departure before arrival, valid seats"""
        cleaned_data = super().clean()
        departure = cleaned_data.get('departure_time')
        arrival = cleaned_data.get('arrival_time')
        available_seats = cleaned_data.get('available_seats')
        bus = cleaned_data.get('bus')
        
        # CHANGE: Validate arrival time is after departure time
        if departure and arrival and arrival <= departure:
            raise forms.ValidationError("Arrival time must be after departure time")
        
        # CHANGE: Validate available seats doesn't exceed bus capacity
        if available_seats and bus and available_seats > bus.capacity:
            raise forms.ValidationError(f"Available seats cannot exceed bus capacity ({bus.capacity})")
        
        # CHANGE: Validate available seats is non-negative
        if available_seats is not None and available_seats < 0:
            raise forms.ValidationError("Available seats cannot be negative")
        
        return cleaned_data


class DriverForm(forms.ModelForm):
    """
    Form for adding/editing Driver records
    CHANGE REASON: Provide validated form fields for driver management
    """
    class Meta:
        model = Driver
        fields = ['license_number', 'license_expiry', 'phone', 'address', 'emergency_contact', 'is_approved', 'is_active']
        widgets = {
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'License number'}),
            'license_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+880 1XXXXXXXXX'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': '3'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+880 1XXXXXXXXX'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_license_number(self):
        """Validate license number uniqueness - CHANGE REASON: Prevent duplicate licenses"""
        license_number = self.cleaned_data.get('license_number')
        if license_number:
            license_number = license_number.strip().upper()
            if Driver.objects.filter(license_number=license_number).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This license number is already registered")
        return license_number


class VehicleIssueForm(forms.ModelForm):
    """
    Form for reporting vehicle issues
    CHANGE REASON: Provide validated form fields for issue reporting
    """
    class Meta:
        model = VehicleIssue
        fields = ['bus', 'issue_description', 'severity']
        widgets = {
            'bus': forms.Select(attrs={'class': 'form-select'}),
            'issue_description': forms.Textarea(attrs={'class': 'form-control', 'rows': '4', 'placeholder': 'Describe the issue...'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        """Filter buses to only active ones - CHANGE REASON: Only report issues on active buses"""
        super().__init__(*args, **kwargs)
        self.fields['bus'].queryset = Bus.objects.filter(is_active=True)