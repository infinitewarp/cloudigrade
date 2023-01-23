"""Internal API URL configuration for cloudigrade."""
from django.conf import settings
from django.urls import include, path
from rest_framework import permissions, renderers, routers
from rest_framework.schemas import get_schema_view

from internal import views, viewsets

# Prepare a list of DRF ViewSet routes.
routes = []

# URLs for slightly different internal versions of public viewset routes.
routes += [
    ("accounts", viewsets.InternalAccountViewSet, "account"),
]

# URLs for common models
# "None" for the third tuple value means to use the model's name.
routes += [
    ("users", viewsets.InternalUserViewSet, "user"),
    ("periodictasks", viewsets.InternalPeriodicTaskViewSet, None),
    ("usertasklocks", viewsets.InternalUserTaskLockViewSet, None),
    ("cloudaccounts", viewsets.InternalCloudAccountViewSet, None),
]

if settings.ENABLE_SYNTHETIC_DATA_REQUEST_HTTP_API:
    routes.append(
        ("syntheticdatarequests", viewsets.InternalSyntheticDataRequestViewSet, None)
    )

# URLs for AWS models
routes += [
    ("awscloudaccounts", viewsets.InternalAwsCloudAccountViewSet, None),
]

# URLs for Azure models
routes += [
    ("azurecloudaccounts", viewsets.InternalAzureCloudAccountViewSet, None),
]


class PermissiveAPIRootView(routers.APIRootView):
    """
    Override default permissions of APIRootView.

    Because DefaultRouter does not provide functionality to pass arguments to define the
    authentication and permission classes for its APIRootView, and our current Django
    configs for cloudigrade have restrictive defaults for authentication and permission,
    we have to force more relaxed settings into a custom class here to allow requests
    to the internal API to access the root view without authentication.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]


router = routers.DefaultRouter()
router.APIRootView = PermissiveAPIRootView

# Register all the DRF ViewSet routes with a common "internal-" basename prefix.
for (prefix, viewset, basename) in routes:
    if not basename:
        basename = router.get_default_basename(viewset)
    basename = f"internal-{basename}"
    router.register(prefix, viewset, basename=basename)

# Prepare a list of Django URL patterns.
urlpatterns = []

# URL Patterns for various automated service checks and metrics.
urlpatterns += [
    path("healthz/", include("health_check.urls")),
    path("", include("django_prometheus.urls")),  # serves "/metrics"
]

# URL patterns for general debugging.
urlpatterns += [
    path("error/", views.fake_error, name="internal-fake-error"),
    path(
        "cdappconfig.json", views.get_cdappconfig_json, name="internal-cdappconfig-json"
    ),
]

# URL patterns for potentially-destructive custom commands.
urlpatterns += [
    path("cache/<str:key>/", views.cache_keys, name="internal-cache"),
    path("clear_cache/", views.clear_cache, name="internal-clear-cache"),
    path(
        "delete_cloud_accounts_not_in_sources/",
        views.delete_cloud_accounts_not_in_sources,
        name="internal-delete-cloud-accounts-not-in-sources",
    ),
    path(
        "migrate_account_numbers_to_org_ids/",
        views.migrate_account_numbers_to_org_ids,
        name="migrate-account-numbers-to-org-ids",
    ),
    path("redis_raw/", views.redis_raw, name="internal-redis-raw"),
    path("tasks/", views.task_run, name="internal-task-run"),
    path(
        "tasks/<str:async_result_id>/",
        views.task_get,
        name="internal-task-collect",
    ),
    path("sources_kafka/", views.sources_kafka, name="internal-sources-kafka"),
]

# URL patterns for accessing various models.
urlpatterns += [
    path("api/cloudigrade/v1/", include(router.urls)),
    path(
        "api/cloudigrade/v1/availability_status",
        views.availability_check,
        name="internal-availability-status",
    ),
    path(
        "openapi.json",
        get_schema_view(
            title="Cloudigrade Internal API",
            renderer_classes=[renderers.JSONOpenAPIRenderer],
            permission_classes=[permissions.AllowAny],
            authentication_classes=[],
            public=True,
            url="/internal/",
            urlconf="internal.urls",
        ),
        name="openapi-schema-internal",
    ),
]
