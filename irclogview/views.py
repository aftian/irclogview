from datetime import datetime, timedelta

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.contrib import auth
from django.core.urlresolvers import reverse

from .models import Channel, Log, Bookmark
from .utils import update_logs

def _update_logs(f):
    def _func(request, *args, **kwargs):
        update_logs()
        return f(request, *args, **kwargs)
    return _func

@_update_logs
def index(request):
    channels = Channel.objects.all()
    if len(channels) == 1:
        channel = channels[0]
        return HttpResponseRedirect(channel.get_absolute_url())

    context = {'channels': channels}
    return render_to_response('irclogview/index.html', context,
                              context_instance=RequestContext(request))

@_update_logs
def channel_index(request, name):
    channel = get_object_or_404(Channel, name=name)
    logs = Log.objects.filter(channel=channel)

    if len(logs) > 0:
        log = logs[0]
        return HttpResponseRedirect(log.get_absolute_url())

    context = {'channel': channel}
    return render_to_response('irclogview/empty.html', context,
                              context_instance=RequestContext(request))

@_update_logs
def show_log(request, name, year, month, day):
    year, month, day = map(int, [year, month, day])

    channel = get_object_or_404(Channel, name=name)
    date = datetime(year, month, day).date()

    # The day's log
    log = get_object_or_404(Log, channel=channel, date=date)

    # Month summary
    if month == 1:
        first = datetime(year-1, 12, 1)
    else:
        first = datetime(year, month-1, 1)
    if month == 12:
        last = datetime(year+1, 1, 31)
    else:
        last = datetime(year, month+1, 1)
    logs = Log.objects.filter(channel=channel,
                              date__gt=first.date(),
                              date__lt=last.date())
    dates = set(logs.values_list('date', flat=True))

    # Never cache recently updated Log (less than 1 day)
    use_cache = log.updated - datetime.now() < timedelta(seconds=86400)

    context = {'log': log,
               'date': date,
               'log_dates': dates,
               'cache_timeout': settings.IRCLOGVIEW_CACHE_TIMEOUT,
               'use_cache': use_cache}
    return render_to_response('irclogview/show_log.html', context,
                              context_instance=RequestContext(request))

@_update_logs
def bookmark_index(request, name):
    channel = get_object_or_404(Channel, name=name)
    bookmarks = Bookmark.objects.filter(log__channel=channel) \
                                .order_by('-log__date') \
                                .select_related()

    context = {'bookmarks': bookmarks,
               'channel': channel}
    return render_to_response('irclogview/bookmark_index.html', context,
                              context_instance=RequestContext(request))

@_update_logs
def bookmark_show(request, name, path):
    channel = get_object_or_404(Channel, name=name)
    bookmark = get_object_or_404(Bookmark, log__channel=channel, path=path)

    url = bookmark.log.get_absolute_url()
    if bookmark.line is not None:
        url = '%s#L%s' % (url, bookmark.line)
    return HttpResponseRedirect(url)

def login(request):
    return HttpResponseRedirect(reverse('openid-login'))

def logout(request):
    auth.logout(request)
    return HttpResponseRedirect(reverse('irclogview_index'))

