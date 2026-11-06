from django.urls import path
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from market import views
from market import trade_views, media_views, deployment
urlpatterns = [
    path('api/health/', deployment.health, name='health'),
    path('admin/deployment-check/', deployment.deployment_check, name='deployment_check'),
    path('uploads/<str:name>/', media_views.database_image, name='database_image'),
    path('admin/', admin.site.urls),
    path('trades/', trade_views.trades, name='trades'),
    path('trades/grant/', trade_views.grant, name='grant'),
    path('products/<int:pk>/chat/', trade_views.start_chat, name='start_chat'),
    path('chats/<int:pk>/', trade_views.chat, name='chat'),
    path('chats/<int:pk>/meeting/', trade_views.share_meeting, name='share_meeting'),
    path('chats/<int:pk>/propose/', trade_views.propose_order, name='propose_order'),
    path('orders/<int:pk>/', trade_views.order_detail, name='order'),
    path('orders/<int:pk>/action/', trade_views.act_order, name='act_order'),
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='auth.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('publish/', views.publish, name='publish'),
    path('mine/', views.mine, name='mine'),
    path('center/', views.center, name='center'),
    path('account/settings/', views.account_settings, name='account_settings'),
    path('account/password/', auth_views.PasswordChangeView.as_view(template_name='password_change.html', success_url='/account/password/done/'), name='password_change'),
    path('account/password/done/', auth_views.PasswordChangeDoneView.as_view(template_name='password_done.html'), name='password_change_done'),
    path('products/<int:pk>/report/', views.report_product, name='report_product'),
    path('reports/', views.reports, name='reports'),
    path('users/<int:user_id>/', views.profile, name='profile'),
    path('center/settings/', views.profile_settings, name='profile_settings'),
    path('products/<int:pk>/state/', views.sale_state, name='sale_state'),
    path('favorites/', views.favorites, name='favorites'),
    path('products/<int:pk>/', views.detail, name='detail'),
    path('products/<int:pk>/edit/', views.edit, name='edit'),
    path('products/<int:pk>/delete/', views.delete, name='delete'),
    path('products/<int:pk>/favorite/', views.favorite, name='favorite'),
    path('api/predict/', views.predict, name='predict'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
