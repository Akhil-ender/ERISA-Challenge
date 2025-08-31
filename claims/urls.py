from django.urls import path
from . import views

app_name = 'claims'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('claims/', views.claim_list, name='claim_list'),
    path('claims/<int:claim_id>/', views.claim_detail, name='claim_detail'),
    path('claims/<int:claim_id>/toggle-flag/', views.toggle_flag, name='toggle_flag'),
    path('claims/<int:claim_id>/add-note/', views.add_note, name='add_note'),
    path('claims/<int:claim_id>/update-status/', views.update_status, name='update_status'),
    path('search/', views.search_claims, name='search_claims'),
    path('csv-upload/', views.csv_upload, name='csv_upload'),
    path('export-csv/', views.export_csv, name='export_csv'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.user_register, name='register'),
    path('profile/', views.user_profile, name='profile'),
]
