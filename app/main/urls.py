from django.urls import path
from . import views

urlpatterns = [
    path('', views.MainView.as_view(), name='main'),
    path('events/', views.EventListView.as_view(), name='events'),
    path('kanban/', views.KanbanView.as_view(), name='kanban'),
    path('create_item/', views.CreateItemView.as_view(), name='create_item'),
    path('edit_item/', views.EditItemView.as_view(), name='edit_item'),
    path('create_kanban_card/', views.CreateKanbanCardView.as_view(), name='create_kanban_card'),
    path('edit_kanban_card/', views.EditKanbanCardView.as_view(), name='edit_kanban_card'),
    path('update_item_status/', views.UpdateItemStatusView.as_view(), name='update_item_status'),
    path('delete_kanban_card/', views.DeleteKanbanCardView.as_view(), name='delete_kanban_card'),
    path('delete_item/', views.DeleteItemView.as_view(), name='delete_item'),
    path('edit/<str:item_type>/<int:item_id>/', views.EditItemPageView.as_view(), name='edit_item_page'),
    path('get_item/<str:item_type>/<int:item_id>/', views.GetItemView.as_view(), name='get_item'),
    path('get_items/', views.GetItemsView.as_view(), name='get_items'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
]