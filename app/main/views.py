from django.views.generic import TemplateView, ListView
from django.views import View
from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse
from .models import Event, Task, KanbanCard, UserProfile
from django.utils import timezone
from datetime import timedelta
import json
import logging
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from .forms import RegisterForm

# Налаштування логування
logger = logging.getLogger(__name__)

@method_decorator(login_required, name='dispatch')
class MainView(TemplateView):
    template_name = 'main/main.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Tasko'
        now = timezone.now()
        end_time = now + timedelta(hours=24)

        user = self.request.user
        events = Event.objects.filter(
            user=user,
            start_time__gte=now,
            start_time__lte=end_time
        ).order_by('start_time')

        tasks = Task.objects.filter(
            user=user,
            start_time__gte=now,
            start_time__lte=end_time
        ).order_by('start_time')

        items = []
        for event in events:
            time_until = (event.start_time - now).total_seconds() / 60
            is_in_progress = now >= event.start_time and (event.end_time is None or now <= event.end_time)
            time_str = f"{int(time_until)} хвилин" if time_until < 60 else f"{int(time_until // 60)} годин"
            items.append({
                'item': event,
                'type': 'event',
                'time_until': time_str,
                'is_in_progress': is_in_progress,
                'start_time': event.start_time
            })
        for task in tasks:
            time_until = (task.start_time - now).total_seconds() / 60
            time_str = f"{int(time_until)} хвилин" if time_until < 60 else f"{int(time_until // 60)} годин"
            items.append({
                'item': task,
                'type': 'task',
                'time_until': time_str,
                'is_in_progress': False,
                'start_time': task.start_time
            })

        items.sort(key=lambda x: x['start_time'])
        context['items'] = items
        return context

@method_decorator(login_required, name='dispatch')
class EventListView(TemplateView):
    template_name = 'main/event_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        start_date = now.date()
        end_date = start_date + timedelta(days=31) if start_date.month == 5 else start_date + timedelta(days=28)
        user = self.request.user
        events = Event.objects.filter(
            user=user,
            start_time__date__range=(start_date, end_date)
        ).order_by('start_time__date')
        tasks = Task.objects.filter(
            user=user,
            start_time__date__range=(start_date, end_date)
        ).order_by('start_time__date')

        days_with_events = {}
        for event in events:
            date = event.start_time.date()
            if date not in days_with_events:
                days_with_events[date] = {'events': [], 'tasks': []}
            days_with_events[date]['events'].append(event)
        for task in tasks:
            date = task.start_time.date()
            if date not in days_with_events:
                days_with_events[date] = {'events': [], 'tasks': []}
            days_with_events[date]['tasks'].append(task)

        context['days_with_events'] = days_with_events
        context['start_date'] = start_date
        context['end_date'] = end_date
        return context

@method_decorator(login_required, name='dispatch')
class KanbanView(TemplateView):
    template_name = 'main/kanban.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        cards = KanbanCard.objects.filter(user=user)
        columns = {
            'todo': [],
            'in_progress': [],
            'done': []
        }
        for card in cards:
            columns[card.status].append(card)
        context['columns'] = columns
        return context

@method_decorator(login_required, name='dispatch')
class CreateItemView(View):
    def post(self, request, *args, **kwargs):
        logger.info(f"Request body: {request.body.decode('utf-8')}")
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
            logger.info(f"Parsed data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)

        item_type = data.get('item_type')
        title = data.get('title')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        description = data.get('description', '')
        is_recurring = data.get('is_recurring', False)
        repeat_interval = data.get('repeat_interval', 1)
        repeat_count = data.get('repeat_count', 1)

        logger.info(f"Item type: {item_type}, Title: {title}, Start time: {start_time}, End time: {end_time}")
        if not item_type or not title or not start_time:
            logger.warning("Missing required fields")
            return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)

        try:
            if item_type == 'event':
                event = Event.objects.create(
                    title=title,
                    start_time=timezone.datetime.fromisoformat(start_time),
                    end_time=timezone.datetime.fromisoformat(end_time) if end_time else None,
                    description=description,
                    user=request.user
                )
                if is_recurring:
                    for i in range(repeat_count):
                        Event.objects.create(
                            title=title,
                            start_time=event.start_time + timedelta(days=repeat_interval * (i + 1)),
                            end_time=event.end_time + timedelta(days=repeat_interval * (i + 1)) if event.end_time else None,
                            description=description,
                            user=request.user
                        )
            elif item_type == 'task':
                Task.objects.create(
                    title=title,
                    start_time=timezone.datetime.fromisoformat(start_time),
                    description=description,
                    user=request.user
                )
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid item type'}, status=400)
        except ValueError as e:
            logger.error(f"Value error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

        return JsonResponse({'status': 'success'})

@method_decorator(login_required, name='dispatch')
class EditItemView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)

        item_type = data.get('item_type')
        item_id = data.get('id')
        title = data.get('title')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        description = data.get('description', '')

        user = request.user
        if item_type == 'event':
            item = get_object_or_404(Event, id=item_id, user=user)
            item.title = title
            item.start_time = timezone.datetime.fromisoformat(start_time)
            item.end_time = timezone.datetime.fromisoformat(end_time) if end_time else None
            item.description = description
            item.save()
        elif item_type == 'task':
            item = get_object_or_404(Task, id=item_id, user=user)
            item.title = title
            item.start_time = timezone.datetime.fromisoformat(start_time)
            item.description = description
            item.save()

        return JsonResponse({'status': 'success'})

@method_decorator(login_required, name='dispatch')
class CreateKanbanCardView(View):
    def post(self, request, *args, **kwargs):
        logger.info(f"Request body: {request.body.decode('utf-8')}")
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
            logger.info(f"Parsed data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)

        title = data.get('title')
        description = data.get('description', '')
        extra_fields = data.get('extra_fields', {})
        status = data.get('status', 'todo')

        if not title:
            logger.warning("Missing required field: title")
            return JsonResponse({'status': 'error', 'message': 'Missing required field: title'}, status=400)

        user = request.user
        card = KanbanCard.objects.create(
            title=title,
            description=description,
            extra_fields=extra_fields,
            status=status,
            user=user
        )
        return JsonResponse({'status': 'success', 'card': {
            'id': card.id,
            'title': card.title,
            'description': card.description,
            'extra_fields': card.extra_fields,
            'status': card.status
        }})

@method_decorator(login_required, name='dispatch')
class EditKanbanCardView(View):
    def post(self, request, *args, **kwargs):
        logger.info(f"Request body: {request.body.decode('utf-8')}")
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)

        card_id = data.get('id')
        title = data.get('title')
        description = data.get('description')
        extra_fields = data.get('extra_fields', {})

        if not card_id or not title:
            return JsonResponse({'status': 'error', 'message': 'Missing required fields: id or title'}, status=400)

        user = request.user
        card = get_object_or_404(KanbanCard, id=card_id, user=user)
        card.title = title
        card.description = description
        card.extra_fields = extra_fields
        card.save()
        return JsonResponse({'status': 'success', 'card': {
            'id': card.id,
            'title': card.title,
            'description': card.description,
            'extra_fields': card.extra_fields,
            'status': card.status
        }})

@method_decorator(login_required, name='dispatch')
class UpdateItemStatusView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)

        card_id = data.get('id')
        status = data.get('status')

        user = request.user
        card = get_object_or_404(KanbanCard, id=card_id, user=user)
        card.status = status
        card.save()
        return JsonResponse({'status': 'success', 'card': {
            'id': card.id,
            'title': card.title,
            'description': card.description,
            'extra_fields': card.extra_fields,
            'status': card.status
        }})

@method_decorator(login_required, name='dispatch')
class DeleteKanbanCardView(View):
    def post(self, request, *args, **kwargs):
        logger.info(f"Request body: {request.body.decode('utf-8')}")
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
            logger.info(f"Parsed data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)

        card_id = data.get('id')
        if not card_id:
            logger.warning("Missing required field: id")
            return JsonResponse({'status': 'error', 'message': 'Missing required field: id'}, status=400)

        user = request.user
        card = get_object_or_404(KanbanCard, id=card_id, user=user)
        card.delete()
        return JsonResponse({'status': 'success'})

@method_decorator(login_required, name='dispatch')
class DeleteItemView(View):
    def post(self, request, *args, **kwargs):
        logger.info(f"Request body: {request.body.decode('utf-8')}")
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else {}
            logger.info(f"Parsed data: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)

        item_id = data.get('id')
        item_type = data.get('item_type')

        if not item_id or not item_type:
            logger.warning("Missing required fields: id or item_type")
            return JsonResponse({'status': 'error', 'message': 'Missing required fields: id or item_type'}, status=400)

        user = request.user
        if item_type == 'event':
            item = get_object_or_404(Event, id=item_id, user=user)
        elif item_type == 'task':
            item = get_object_or_404(Task, id=item_id, user=user)
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid item type'}, status=400)

        item.delete()
        return JsonResponse({'status': 'success'})

@method_decorator(login_required, name='dispatch')
class EditItemPageView(TemplateView):
    template_name = 'main/edit_event.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item_type = self.kwargs['item_type']
        item_id = self.kwargs['item_id']
        user = self.request.user

        if item_type == 'event':
            item = get_object_or_404(Event, id=item_id, user=user)
        elif item_type == 'task':
            item = get_object_or_404(Task, id=item_id, user=user)
        else:
            raise ValueError("Invalid item type")

        context['item'] = item
        context['item_type'] = item_type
        return context

@method_decorator(login_required, name='dispatch')
class GetItemView(View):
    def get(self, request, *args, **kwargs):
        item_type = self.kwargs['item_type']
        item_id = self.kwargs['item_id']
        user = request.user

        if item_type == 'event':
            item = get_object_or_404(Event, id=item_id, user=user)
        elif item_type == 'task':
            item = get_object_or_404(Task, id=item_id, user=user)
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid item type'})

        data = {
            'id': item.id,
            'title': item.title,
            'start_time': item.start_time.isoformat(),
            'end_time': item.end_time.isoformat() if hasattr(item, 'end_time') and item.end_time else None,
            'description': item.description if hasattr(item, 'description') else ''
        }
        return JsonResponse(data)

@method_decorator(login_required, name='dispatch')
class GetItemsView(View):
    def get(self, request, *args, **kwargs):
        date_str = request.GET.get('date')
        try:
            date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            date = timezone.now().date()

        user = request.user
        events = Event.objects.filter(start_time__date=date, user=user)
        tasks = Task.objects.filter(start_time__date=date, user=user)

        items = []
        for event in events:
            items.append({
                'id': event.id,
                'type': 'event',
                'title': event.title,
                'start_time': event.start_time.isoformat(),
                'end_time': event.end_time.isoformat() if event.end_time else None,
                'description': event.description if event.description else ''
            })
        for task in tasks:
            items.append({
                'id': task.id,
                'type': 'task',
                'title': task.title,
                'start_time': task.start_time.isoformat(),
                'description': task.description if task.description else ''
            })

        return JsonResponse({'items': items})

# Додавання переглядів для автентифікації
class CustomLoginView(LoginView):
    template_name = 'main/login.html'

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('main')

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')

class RegisterView(View):
    template_name = 'main/register.html'

    def get(self, request):
        form = RegisterForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            UserProfile.objects.create(user=user)
            login(request, user)
            return redirect('main')
        return render(request, self.template_name, {'form': form})