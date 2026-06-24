from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('subscribe/', views.signup, name='signup'),
    path('pay/<int:sub_id>/', views.pay, name='pay'),
    path('thanks/<int:sub_id>/', views.thanks, name='thanks'),
    path('download/', views.download_app, name='download_app'),
    path('api/store-config/', views.store_config, name='store_config'),
    path('api/claim-machine/', views.claim_machine, name='claim_machine'),
    path('api/license-status/', views.license_status, name='license_status'),
    path('manage/reset-machine/<int:sub_id>/', views.api_reset_machine, name='api_reset_machine'),
    path('status/', views.status_lookup, name='status_lookup'),
    path('status/<int:sub_id>/', views.status_detail, name='status_detail'),

    path('manage/login/', views.manage_login, name='manage_login'),
    path('manage/logout/', views.manage_logout, name='manage_logout'),
    path('manage/', views.manage, name='manage'),
    path('manage/approve/<int:sub_id>/', views.api_approve, name='api_approve'),
    path('manage/reject/<int:sub_id>/', views.api_reject, name='api_reject'),
]
