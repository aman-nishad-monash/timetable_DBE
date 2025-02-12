from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home page with CSV upload and preferences form
    path('timetable-view/', views.timetable_view, name='timetable_view'),  # Timetable display page
    path('reset/', views.reset_view, name='reset')
]
