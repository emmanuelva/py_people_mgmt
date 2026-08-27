from rest_framework.routers import DefaultRouter

from people import views

app_name = 'people'

router = DefaultRouter()
router.register('', views.PersonViewSet, basename='person')

urlpatterns = router.urls
