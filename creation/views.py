import os
import re
import json
import time
import subprocess
from decimal import Decimal
from urllib2 import urlopen
from hurry.filesize import size
from django.conf import settings
from django.views import generic
from django.contrib import messages
from hurry.filesize import alternative
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group
from django.views.decorators.http import require_POST

from django import forms
from django.template import RequestContext
from django.core.context_processors import csrf
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, render_to_response
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect

from creation.forms import *
from creation.models import *

def is_contributor(user):
    """Check if the user is having contributor rights"""
    if user.groups.filter(Q(name='Contributor')|Q(name='External-Contributor')).count():
        return True
    return False

def is_domainreviewer(user):
    """Check if the user is having domain reviewer rights"""
    if user.groups.filter(name='Domain-Reviewer').count() == 1:
        return True
    return False

def is_qualityreviewer(user):
    """Check if the user is having quality reviewer rights"""
    if user.groups.filter(name='Quality-Reviewer').count() == 1:
        return True
    return False

def is_videoreviewer(user):
    """Check if the user is having video reviewer rights"""
    if user.groups.filter(name='Video-Reviewer').count() == 1:
        return True
    return False

def get_filesize(path):
    filesize_bytes = os.path.getsize(path)
    return size(filesize_bytes, system=alternative)

# returns video meta info using ffmpeg
def get_video_info(path):
    """Uses ffmpeg to determine information about a video."""
    info_m = {}
    try:
        process = subprocess.Popen(['/usr/bin/avconv', '-i', path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = process.communicate()
        duration_m = re.search(r"Duration:\s{1}(?P<hours>\d+?):(?P<minutes>\d+?):(?P<seconds>\d+\.\d+?)", stdout, re.DOTALL).groupdict()
        info_m = re.search(r": Video: (?P<codec>.*?), (?P<profile>.*?), (?P<width>.*?)x(?P<height>.*?), ", stdout, re.DOTALL).groupdict()

        hours = Decimal(duration_m['hours'])
        minutes = Decimal(duration_m['minutes'])
        seconds = Decimal(duration_m['seconds'])

        total = 0
        total += 60 * 60 * hours
        total += 60 * minutes
        total += seconds

        info_m['hours'] = hours
        info_m['minutes'] = minutes
        info_m['seconds'] = seconds
        tmp_seconds = str(int(seconds))
        if seconds < 10:
            tmp_seconds = "0" + tmp_seconds
        info_m['duration'] = duration_m['hours'] + ':' + duration_m['minutes'] + ":" + tmp_seconds
        info_m['total'] = int(total)
        info_m['width'] = int(info_m['width'])
        info_m['height'] = int(info_m['height'])
        info_m['size'] = get_filesize(path)
    except:
        info_m['codec'] = ''
        info_m['profile'] = ''
        info_m['hours'] = 0
        info_m['minutes'] = 0
        info_m['seconds'] = 0
        info_m['duration'] = 0
        info_m['total'] = 0
        info_m['width'] = 0
        info_m['height'] = 0
        info_m['size'] = 0
    return info_m

def add_qualityreviewer_notification(tr_rec, comp_title, message):
    dr_roles = QualityReviewerRole.objects.filter(foss_category = tr_rec.tutorial_detail.foss, language = tr_rec.language, status = 1)
    for dr_role in dr_roles:
        QualityReviewerNotification.objects.create(user = dr_role.user, title = comp_title, message = message, tutorial_resource = tr_rec)

def add_domainreviewer_notification(tr_rec, comp_title, message):
    dr_roles = DomainReviewerRole.objects.filter(foss_category = tr_rec.tutorial_detail.foss, language = tr_rec.language, status = 1)
    for dr_role in dr_roles:
        DomainReviewerNotification.objects.create(user = dr_role.user, title = comp_title, message = message, tutorial_resource = tr_rec)

def add_adminreviewer_notification(tr_rec, comp_title, message):
    role = Group.objects.get(name = 'Video-Reviewer')
    users = role.user_set.all()

    for user in users:
        AdminReviewerNotification.objects.create(user = user, title = comp_title, message = message, tutorial_resource = tr_rec)

def add_contributor_notification(tr_rec, comp_title, message):
    con_roles = ContributorRole.objects.filter(foss_category = tr_rec.tutorial_detail.foss, language = tr_rec.language, status = 1)

    for con in con_roles:
        ContributorNotification.objects.create(user = con.user, title = comp_title, message = message, tutorial_resource = tr_rec)

@login_required
def init_creation_app(request):
    try:
        if Group.objects.filter(name = 'Contributor').count() == 0:
            Group.objects.create(name = 'Contributor')
        if Group.objects.filter(name = 'External-Contributor').count() == 0:
            Group.objects.create(name = 'External-Contributor')
        if Group.objects.filter(name = 'Video-Reviewer').count() == 0:
            Group.objects.create(name = 'Video-Reviewer')
        if Group.objects.filter(name = 'Domain-Reviewer').count() == 0:
            Group.objects.create(name = 'Domain-Reviewer')
        if Group.objects.filter(name = 'Quality-Reviewer').count() == 0:
            Group.objects.create(name = 'Quality-Reviewer')
        if Group.objects.filter(name = 'Quality-Reviewer').count() == 0:
            Group.objects.create(name = 'Quality-Reviewer')
        messages.success(request, 'Creation application initialised successfully!')
    except Exception, e:
        messages.error(request, str(e))
    return HttpResponseRedirect('/creation/')

# Creation app dashboard
@login_required
def creationhome(request):
    if is_contributor(request.user) or is_domainreviewer(request.user) or is_videoreviewer(request.user) or is_qualityreviewer(request.user):
        contrib_notifs = []
        admin_notifs = []
        domain_notifs = []
        quality_notifs = []
        if is_contributor(request.user):
            contrib_notifs = ContributorNotification.objects.filter(user = request.user).order_by('-created')
        if is_videoreviewer(request.user):
            admin_notifs = AdminReviewerNotification.objects.filter(user = request.user).order_by('-created')
        if is_domainreviewer(request.user):
            domain_notifs = DomainReviewerNotification.objects.filter(user = request.user).order_by('-created')
        if is_qualityreviewer(request.user):
            quality_notifs = QualityReviewerNotification.objects.filter(user = request.user).order_by('-created')
        context = {
            'contrib_notifs': contrib_notifs,
            'admin_notifs': admin_notifs,
            'domain_notifs': domain_notifs,
            'quality_notifs': quality_notifs,
        }
        context.update(csrf(request))
        return render(request, 'creation/templates/creationhome.html', context)
    else:
        raise PermissionDenied()

# tutorial upload index page
@login_required
def upload_index(request):
    if not is_contributor(request.user):
        raise PermissionDenied()
    if request.method == 'POST':
        form = UploadTutorialForm(request.user, request.POST)
        lang = None
        if form.is_valid():
            lang = Language.objects.get(pk = int(request.POST['language']))
            common_content = TutorialCommonContent()
            if TutorialCommonContent.objects.filter(tutorial_detail_id = request.POST['tutorial_name']).count():
                common_content = TutorialCommonContent.objects.get(tutorial_detail_id = request.POST['tutorial_name'])
            else:
                common_content.tutorial_detail = TutorialDetail.objects.get(pk = request.POST['tutorial_name'])
                common_content.slide_user = request.user
                common_content.code_user = request.user
                common_content.assignment_user = request.user
                common_content.prerequisite_user = request.user
                common_content.keyword_user = request.user
                common_content.save()
            if TutorialResource.objects.filter(tutorial_detail_id = request.POST['tutorial_name'], common_content_id = common_content.id, language_id = request.POST['language']).count():
                tutorial_resource = TutorialResource.objects.get(tutorial_detail_id = request.POST['tutorial_name'], common_content_id = common_content.id, language_id = request.POST['language'])
            else:
                tutorial_resource = TutorialResource()
                tutorial_resource.tutorial_detail = common_content.tutorial_detail
                tutorial_resource.common_content = common_content
                tutorial_resource.language = lang
                tutorial_resource.outline_user = request.user
                tutorial_resource.script_user = request.user
                tutorial_resource.video_user = request.user
                tutorial_resource.save()

            return HttpResponseRedirect('/creation/upload/tutorial/' + str(tutorial_resource.id) + '/')
    else:
        form = UploadTutorialForm(user=request.user)

    context = {
        'form': form,
    }
    context.update(csrf(request))
    return render(request, 'creation/templates/upload_index.html', context)

@csrf_exempt
def ajax_upload_prerequisite(request):
    data = ''
    if request.method == 'POST':
        foss = ''
        try:
            foss = int(request.POST.get('foss'))
            lang_rec = Language.objects.get(name = 'English')
        except:
            foss = ''
        if foss and lang_rec:
            td_list = TutorialDetail.objects.filter(foss_id = foss).values_list('id')
            td_recs = TutorialDetail.objects.filter(
                id__in = TutorialResource.objects.filter(
                    tutorial_detail_id__in = td_list,
                    language_id = lang_rec.id,
                    status = 1
                ).values_list(
                    'tutorial_detail_id'
                )
            )
            for td_rec in td_recs:
                data += '<option value="' + str(td_rec.id) + '">' + td_rec.tutorial + '</option>'
            if data:
                data = '<option value=""></option>' + data
    return HttpResponse(json.dumps(data), mimetype='application/json')

@csrf_exempt
def ajax_upload_foss(request):
    data = ''
    if request.method == 'POST':
        foss = ''
        lang = ''
        try:
            foss = request.POST.get('foss')
            lang = request.POST.get('lang')
        except:
            foss = ''
            lang = ''
        if foss and lang:
            lang_rec = Language.objects.get(pk = int(lang))
            if lang_rec.name == 'English':
                td_list = TutorialDetail.objects.filter(foss_id = foss).values_list('id')
                tutorials = TutorialDetail.objects.filter(
                    id__in = td_list
                ).exclude(
                    id__in = TutorialResource.objects.filter(
                        tutorial_detail_id__in = td_list,
                        language_id = lang_rec.id,
                        status = 1
                    ).values_list(
                        'tutorial_detail_id'
                    )
                )
            else:
                eng_rec = Language.objects.get(name = 'English')
                td_list = TutorialDetail.objects.filter(foss_id = foss).values_list('id')
                tutorials = TutorialDetail.objects.filter(
                    id__in = TutorialResource.objects.filter(
                        tutorial_detail_id__in = td_list,
                        language_id = eng_rec.id,
                        status = 1
                    ).values_list(
                        'tutorial_detail_id'
                    )
                ).exclude(
                    id__in = TutorialResource.objects.filter(
                        tutorial_detail_id__in = td_list,
                        language_id = lang_rec.id,
                        status__gte = 1
                    ).values_list(
                        'tutorial_detail_id'
                    )
                )
            for tutorial in tutorials:
                data += '<option value="' + str(tutorial.id) + '">' + tutorial.tutorial + '</option>'
            if data:
                data = '<option value=""></option>' + data
        elif foss:
            languages = Language.objects.filter(id__in=ContributorRole.objects.filter(user_id=request.user.id, foss_category_id=foss).values_list('language_id'))
            for language in languages:
                data += '<option value="' + str(language.id) + '">' + language.name + '</option>'
            if data:
                data = '<option value=""></option>' + data

    return HttpResponse(json.dumps(data), mimetype='application/json')

@login_required
def upload_tutorial(request, trid):
    tr_rec = None
    contrib_log = None
    review_log = None
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        ContributorRole.objects.get(user_id = request.user.id, foss_category_id = tr_rec.tutorial_detail.foss_id, language_id = tr_rec.language_id, status = 1)
        contrib_log = ContributorLog.objects.filter(tutorial_resource_id = tr_rec.id).order_by('-created')
        review_log = NeedImprovementLog.objects.filter(tutorial_resource_id = tr_rec.id).order_by('-created')
    except Exception, e:
        print e
        raise PermissionDenied()
    context = {
        'tr': tr_rec,
        'contrib_log': contrib_log,
        'review_log': review_log,
        'script_base': settings.SCRIPT_URL,
    }
    context.update(csrf(request))
    return render(request, 'creation/templates/upload_tutorial.html', context)

@login_required
def upload_outline(request, trid):
    tr_rec = None
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        ContributorRole.objects.get(user_id = request.user.id, foss_category_id = tr_rec.tutorial_detail.foss_id, language_id = tr_rec.language_id, status = 1)
    except Exception, e:
        raise PermissionDenied()
    if tr_rec.outline_status > 2 and tr_rec.outline_status != 5:
        raise PermissionDenied()
    response_msg = ''
    error_msg = ''
    warning_msg = ''
    if request.method == 'POST':
        form = UploadOutlineForm(trid, request.POST)
        if form.is_valid():
            try:
                prev_state = tr_rec.outline_status
                if tr_rec.outline != request.POST['outline']:
                    tr_rec.outline = request.POST['outline']
                else:
                    warning_msg = 'There is no change in outline'
                tr_rec.outline_user = request.user
                tr_rec.outline_status = 2
                tr_rec.save()
                ContributorLog.objects.create(status = prev_state, user = request.user, tutorial_resource = tr_rec, component = 'outline')
                comp_title = tr_rec.tutorial_detail.foss.foss + ': ' + tr_rec.tutorial_detail.tutorial + ' - ' + tr_rec.language.name
                add_domainreviewer_notification(tr_rec, comp_title, 'Outline waiting for Domain review')
                response_msg = 'Outline status updated successfully!'
            except Exception, e:
                print e
                error_msg = 'Something went wrong, please try again later.'
        else:
            context = {
                'form': form,
            }
            context.update(csrf(request))
            return render(request, 'creation/templates/upload_outline.html', context)
    form = UploadOutlineForm(trid)
    if response_msg:
        messages.success(request, response_msg)
    if error_msg:
        messages.error(request, error_msg)
    if warning_msg:
        messages.warning(request, warning_msg)
    context = {
        'form': form,
    }
    context.update(csrf(request))
    return render(request, 'creation/templates/upload_outline.html', context)

@login_required
def upload_script(request, trid):
    tr_rec = None
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        ContributorRole.objects.get(user_id = request.user.id, foss_category_id = tr_rec.tutorial_detail.foss_id, language_id = tr_rec.language_id, status = 1)
    except Exception, e:
        raise PermissionDenied()
    if tr_rec.script_status > 2 and tr_rec.script_status != 5:
        raise PermissionDenied()
    response_msg = ''
    error_msg = ''
    storage_path = tr_rec.tutorial_detail.foss.foss + '/' + tr_rec.tutorial_detail.level.code + '/' + tr_rec.tutorial_detail.tutorial.replace(' ', '-') + '/' + tr_rec.language.name
    script_path = settings.SCRIPT_URL + storage_path
    if request.method == 'POST':
        form = UploadScriptForm(script_path, request.POST)
        if form.is_valid():
            try:
                code = 0
                try:
                    code = urlopen(script_path).code
                except Exception, e:
                    code = e.code
                if(int(code) == 200):
                    prev_state = tr_rec.script_status
                    tr_rec.script = storage_path
                    tr_rec.script_user = request.user
                    tr_rec.script_status = 2
                    tr_rec.save()
                    ContributorLog.objects.create(status = prev_state, user = request.user, tutorial_resource = tr_rec, component = 'script')
                    comp_title = tr_rec.tutorial_detail.foss.foss + ': ' + tr_rec.tutorial_detail.tutorial + ' - ' + tr_rec.language.name
                    add_domainreviewer_notification(tr_rec, comp_title, 'Script waiting for domain review')
                    response_msg = 'Script status updated successfully'
                else:
                    error_msg = 'Please update the script to wiki before pressing the submit button.'
            except Exception, e:
                print e
                error_msg = 'Something went wrong, please try again later.'
        else:
            context = {
                'form': form,
                'script_path': script_path,
            }
            context.update(csrf(request))
            return render(request, 'creation/templates/upload_script.html', context)
    form = UploadScriptForm(script_path)
    if error_msg:
        messages.error(request, error_msg)
    if response_msg:
        messages.success(request, response_msg)
    context = {
        'form': form,
        'script_path': script_path,
    }
    context.update(csrf(request))
    return render(request, 'creation/templates/upload_script.html', context)

@login_required
def upload_prerequisite(request, trid):
    tr_rec = None
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        ContributorRole.objects.get(user_id = request.user.id, foss_category_id = tr_rec.tutorial_detail.foss_id, language_id = tr_rec.language_id, status = 1)
    except Exception, e:
        raise PermissionDenied()
    if tr_rec.common_content.prerequisite_status > 2 and tr_rec.common_content.prerequisite_status != 5:
        raise PermissionDenied()
    response_msg = ''
    error_msg = ''
    warning_msg = ''
    if request.method == 'POST':
        form = UploadPrerequisiteForm(request.user, request.POST)
        if form.is_valid():
            try:
                prev_state = tr_rec.common_content.prerequisite_status
                if tr_rec.common_content.prerequisite_id != request.POST['tutorial_name']:
                    tr_rec.common_content.prerequisite_id = request.POST['tutorial_name']
                else:
                    warning_msg = 'There is no change in Prerequisite'
                tr_rec.common_content.prerequisite_user = request.user
                tr_rec.common_content.prerequisite_status = 2
                tr_rec.common_content.save()
                ContributorLog.objects.create(status = prev_state, user = request.user, tutorial_resource = tr_rec, component = 'prerequisite')
                comp_title = tr_rec.tutorial_detail.foss.foss + ': ' + tr_rec.tutorial_detail.tutorial + ' - ' + tr_rec.language.name
                add_domainreviewer_notification(tr_rec, comp_title, 'Prerequisite waiting for Domain review')
                response_msg = 'Prerequisite status updated successfully!'
            except Exception, e:
                error_msg = 'Something went wrong, please try again later.'
        else:
            context = {
                'form': form,
            }
            context.update(csrf(request))
            return render(request, 'creation/templates/upload_prerequisite.html', context)
    form = UploadPrerequisiteForm(request.user)
    if response_msg:
        messages.success(request, response_msg)
    if error_msg:
        messages.error(request, error_msg)
    if warning_msg:
        messages.warning(request, warning_msg)
    context = {
        'form': form,
    }
    context.update(csrf(request))
    return render(request, 'creation/templates/upload_prerequisite.html', context)

@login_required
def upload_keywords(request, trid):
    tr_rec = None
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        ContributorRole.objects.get(user_id = request.user.id, foss_category_id = tr_rec.tutorial_detail.foss_id, language_id = tr_rec.language_id, status = 1)
    except Exception, e:
        raise PermissionDenied()
    if tr_rec.common_content.keyword_status > 2 and tr_rec.common_content.keyword_status != 5:
        raise PermissionDenied()
    response_msg = ''
    error_msg = ''
    warning_msg = ''
    if request.method == 'POST':
        form = UploadKeywordsForm(trid, request.POST)
        if form.is_valid():
            try:
                prev_state = tr_rec.common_content.keyword_status
                if tr_rec.common_content.keyword != request.POST['keywords']:
                    tr_rec.common_content.keyword = request.POST['keywords']
                else:
                    warning_msg = 'There is no change in keywords'
                tr_rec.common_content.keyword_user = request.user
                tr_rec.common_content.keyword_status = 2
                tr_rec.common_content.save()
                ContributorLog.objects.create(status = prev_state, user = request.user, tutorial_resource = tr_rec, component = 'keyword')
                comp_title = tr_rec.tutorial_detail.foss.foss + ': ' + tr_rec.tutorial_detail.tutorial + ' - ' + tr_rec.language.name
                add_domainreviewer_notification(tr_rec, comp_title, 'Keywords waiting for Domain review')
                response_msg = 'Keywords status updated successfully!'
            except Exception, e:
                error_msg = 'Something went wrong, please try again later.'
        else:
            context = {
                'form': form,
            }
            context.update(csrf(request))
            return render(request, 'creation/templates/upload_keywords.html', context)
    form = UploadKeywordsForm(trid)
    if response_msg:
        messages.success(request, response_msg)
    if error_msg:
        messages.error(request, error_msg)
    if warning_msg:
        messages.warning(request, warning_msg)
    context = {
        'form': form,
    }
    context.update(csrf(request))
    return render(request, 'creation/templates/upload_keywords.html', context)

@login_required
def upload_component(request, trid, component):
    tr_rec = None
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        ContributorRole.objects.get(user_id = request.user.id, foss_category_id = tr_rec.tutorial_detail.foss_id, language_id = tr_rec.language_id, status = 1)
        comp_title = tr_rec.tutorial_detail.foss.foss + ': ' + tr_rec.tutorial_detail.tutorial + ' - ' + tr_rec.language.name
    except Exception, e:
        raise PermissionDenied()
    if component == 'video' and getattr(tr_rec, component + '_status') == 4:
        raise PermissionDenied()
    elif (component == 'slide' or component == 'code' or component == 'assignment') and getattr(tr_rec.common_content, component + '_status') == 4:
        raise PermissionDenied()
    else:
        if request.method == 'POST':
            response_msg = ''
            error_msg = ''
            form = ComponentForm(component, request.POST, request.FILES)
            if form.is_valid():
                try:
                    comp_log = ContributorLog()
                    comp_log.user = request.user
                    comp_log.tutorial_resource = tr_rec
                    comp_log.component = component
                    if component == 'video':
                        file_name, file_extension = os.path.splitext(request.FILES['comp'].name)
                        file_name =  tr_rec.tutorial_detail.tutorial.replace(' ', '-') + '-' + tr_rec.language.name + file_extension
                        file_path = settings.MEDIA_ROOT + 'videos/' + str(tr_rec.tutorial_detail.foss_id) + '/' + str(tr_rec.tutorial_detail.id) + '/'
                        full_path = file_path + file_name
                        if os.path.isfile(file_path + tr_rec.video) and tr_rec.video_status > 0:
                            if 'isarchive' in request.POST and int(request.POST['isarchive']) > 0:
                                archived_file = 'Archived-' + str(request.user.id) + '-' + str(int(time.time())) + '-' + tr_rec.video
                                os.rename(file_path + tr_rec.video, file_path + archived_file)
                                ArchivedVideo.objects.create(tutorial_resource = tr_rec, user = request.user, version = tr_rec.version, video = archived_file, atype = tr_rec.video_status)
                                if int(request.POST['isarchive']) == 2:
                                    tr_rec.version += 1
                        fout = open(full_path, 'wb+')
                        f = request.FILES['comp']
                        # Iterate through the chunks.
                        for chunk in f.chunks():
                            fout.write(chunk)
                        fout.close()
                        comp_log.status = tr_rec.video_status
                        tr_rec.video = file_name
                        tr_rec.video_user = request.user
                        tr_rec.video_status = 1
                        if not tr_rec.version:
                            tr_rec.version = 1
                        tr_rec.save()
                        comp_log.save()
                        comp_title = tr_rec.tutorial_detail.foss.foss + ': ' + tr_rec.tutorial_detail.tutorial + ' - ' + tr_rec.language.name
                        add_adminreviewer_notification(tr_rec, comp_title, 'Video waiting for admin review')
                        response_msg = 'Video uploaded successfully!'
                    elif component == 'slide':
                        file_name, file_extension = os.path.splitext(request.FILES['comp'].name)
                        file_name =  tr_rec.tutorial_detail.tutorial.replace(' ', '-') + '-Slides' + file_extension
                        file_path = settings.MEDIA_ROOT + 'videos/' + str(tr_rec.tutorial_detail.foss_id) + '/' + str(tr_rec.tutorial_detail.id) + '/resources/' + file_name
                        fout = open(file_path, 'wb+')
                        f = request.FILES['comp']
                        # Iterate through the chunks.
                        for chunk in f.chunks():
                            fout.write(chunk)
                        fout.close()
                        comp_log.status = tr_rec.common_content.slide_status
                        tr_rec.common_content.slide = file_name
                        tr_rec.common_content.slide_status = 2
                        tr_rec.common_content.slide_user = request.user
                        tr_rec.common_content.save()
                        comp_log.save()
                        add_domainreviewer_notification(tr_rec, comp_title, component.title() + ' waiting for domain review')
                        response_msg = 'Slides uploaded successfully!'
                    elif component == 'code':
                        file_name, file_extension = os.path.splitext(request.FILES['comp'].name)
                        file_name =  tr_rec.tutorial_detail.tutorial.replace(' ', '-') + '-Codefiles' + file_extension
                        file_path = settings.MEDIA_ROOT + 'videos/' + str(tr_rec.tutorial_detail.foss_id) + '/' + str(tr_rec.tutorial_detail.id) + '/resources/' + file_name
                        fout = open(file_path, 'wb+')
                        f = request.FILES['comp']
                        # Iterate through the chunks.
                        for chunk in f.chunks():
                            fout.write(chunk)
                        fout.close()
                        comp_log.status = tr_rec.common_content.code_status
                        tr_rec.common_content.code = file_name
                        tr_rec.common_content.code_status = 2
                        tr_rec.common_content.code_user = request.user
                        tr_rec.common_content.save()
                        comp_log.save()
                        add_domainreviewer_notification(tr_rec, comp_title, component.title() + ' waiting for domain review')
                        response_msg = 'Code files uploaded successfully!'
                    elif component == 'assignment':
                        file_name, file_extension = os.path.splitext(request.FILES['comp'].name)
                        file_name =  tr_rec.tutorial_detail.tutorial.replace(' ', '-') + '-Assignment' + file_extension
                        file_path = settings.MEDIA_ROOT + 'videos/' + str(tr_rec.tutorial_detail.foss_id) + '/' + str(tr_rec.tutorial_detail.id) + '/resources/' + file_name
                        fout = open(file_path, 'wb+')
                        f = request.FILES['comp']
                        # Iterate through the chunks.
                        for chunk in f.chunks():
                            fout.write(chunk)
                        fout.close()
                        comp_log.status = tr_rec.common_content.assignment_status
                        tr_rec.common_content.assignment = file_name
                        tr_rec.common_content.assignment_status = 2
                        tr_rec.common_content.assignment_user = request.user
                        tr_rec.common_content.save()
                        comp_log.save()
                        add_domainreviewer_notification(tr_rec, comp_title, component.title() + ' waiting for domain review')
                        response_msg = 'Assignment file uploaded successfully!'
                except Exception, e:
                    error_msg = 'Something went wrong, please try again later.'
                form = ComponentForm(component)
                if response_msg:
                    messages.success(request, response_msg)
                if error_msg:
                    messages.error(request, error_msg)
                context = {
                    'form': form,
                    'tr': tr_rec,
                    'title': component,
                }
                context.update(csrf(request))
                return render(request, 'creation/templates/upload_component.html', context)
            else:
                context = {
                    'form': form,
                    'tr': tr_rec,
                    'title': component,
                }
                context.update(csrf(request))
                return render(request, 'creation/templates/upload_component.html', context)
        
    form = ComponentForm(component)
    context = {
        'form': form,
        'tr': tr_rec,
        'title': component,
    }
    context.update(csrf(request))
    return render(request, 'creation/templates/upload_component.html', context)

@login_required
def mark_notrequired(request, trid, tcid, component):
    tcc = None
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        ContributorRole.objects.get(user_id = request.user.id, foss_category_id = tr_rec.tutorial_detail.foss_id, language_id = tr_rec.language_id, status = 1)
    except Exception, e:
        raise PermissionDenied()
    try:
        tcc = TutorialCommonContent.objects.get(pk = tcid)
        if getattr(tcc, component + '_status') == 0:
            prev_state = getattr(tcc, component + '_status')
            setattr(tcc, component + '_status', 6)
            setattr(tcc, component + '_user_id', request.user.id)
            tcc.save()
            ContributorLog(user = request.user, tutorial_resource_id = trid, component = component, status = prev_state)
            messages.success(request, component.title() + " status updated successfully!")
        else:
            messages.error(request, "Invalid resource id!")
    except Exception, e:
        messages.error(request, 'Something went wrong, please try after some time.')
    return HttpResponseRedirect(request.META['HTTP_REFERER'])

def view_component(request, trid, component):
    tr_rec = None
    context = {}
    try:
        tr_rec = TutorialResource.objects.get(pk = trid)
    except Exception, e:
        print e
        raise PermissionDenied()
    if component == 'outline':
        context = {
            'component': component,
            'component_data': tr_rec.outline
        }
    elif component == 'keyword':
        context = {
            'component': component,
            'component_data': tr_rec.common_content.keyword
        }
    elif component == 'video':
        video_path = settings.MEDIA_ROOT + "videos/" + str(tr_rec.tutorial_detail.foss_id) + "/" + str(tr_rec.tutorial_detail_id) + "/" + tr_rec.video
        video_info = get_video_info(video_path)
        context = {
            'tr': tr_rec,
            'component': component,
            'video_info': video_info,
            'media_url': settings.MEDIA_URL
        }
    else:
        messages.error(request, 'Invalid component passed as argument!')
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    context.update(csrf(request))
    return render(request, 'creation/templates/view_component.html', context)

@login_required
def tutorials_contributed(request):
    tmp_recs = []
    if is_contributor(request.user):
        foss_contrib_list = ContributorRole.objects.filter(user = request.user, status = 1)
        for foss_contrib in foss_contrib_list:
            tr_recs = TutorialResource.objects.select_related().filter(tutorial_detail_id__in = TutorialDetail.objects.filter(foss_id = foss_contrib.foss_category_id).values_list('id'), language_id = foss_contrib.language_id)
            for tr_rec in tr_recs:
                flag = 1
                if tr_rec.language.name == 'English' and (tr_rec.common_content.slide_user_id != request.user.id or tr_rec.common_content.slide_status == 0) and (tr_rec.common_content.code_user_id != request.user.id or tr_rec.common_content.code_status == 0) and (tr_rec.common_content.assignment_user_id != request.user.id or tr_rec.common_content.assignment_status == 0) and (tr_rec.common_content.keyword_user_id != request.user.id or tr_rec.common_content.keyword_status == 0):
                    flag = 0
                else:
                    flag = 0
                if flag == 1 or (tr_rec.outline_user_id == request.user.id and tr_rec.outline_status > 0) or (tr_rec.script_user_id == request.user.id and tr_rec.script_status > 0) or (tr_rec.video_user_id == request.user.id and tr_rec.video_status > 0):
                    tmp_recs.append(tr_rec)
        context = {
            'tr_recs': tmp_recs,
            'media_url': settings.MEDIA_URL
        }
        return render(request, 'creation/templates/my_contribs.html', context)
    else:
        raise PermissionDenied()

@login_required
def admin_review_index(request):
    if not is_videoreviewer(request.user):
        raise PermissionDenied()
    tr_recs = None
    try:
        tr_recs = TutorialResource.objects.filter(video_status = 1, status = 0).order_by('updated')
        context = {
            'tr_recs': tr_recs
        }
        return render(request, 'creation/templates/admin_review_index.html', context)
    except Exception, e:
        return e

@login_required
def admin_review_video(request, trid):
    if not is_videoreviewer(request.user):
        raise PermissionDenied()
    try:
        tr = TutorialResource.objects.select_related().get(pk = trid, status = 0, video_status = 1)
        tut_title = tr.tutorial_detail.foss.foss + ': ' + tr.tutorial_detail.tutorial + ' - ' + tr.language.name
    except:
        raise PermissionDenied()
    response_msg = ''
    error_msg = ''
    if request.method == 'POST':
        form = ReviewVideoForm(request.POST)
        if form.is_valid():
            form = ReviewVideoForm()
            if request.POST['video_status'] == '2':
                try:
                    tr.video_status = 2
                    tr.save()
                    AdminReviewLog.objects.create(status = tr.video_status, user = request.user, tutorial_resource = tr)
                    add_contributor_notification(tr, tut_title, 'Video accepted by Admin reviewer')
                    add_domainreviewer_notification(tr, tut_title, 'Video waiting for Domain review')
                    response_msg = 'Review status updated successfully!'
                except Exception, e:
                    error_msg = 'Something went wrong, please try again later.'
            elif request.POST['video_status'] == '5':
                try:
                    prev_state = tr.video_status
                    tr.video_status = 5
                    tr.save()
                    NeedImprovementLog.objects.create(user = request.user, tutorial_resource = tr, review_state = prev_state, component = 'video', comment = request.POST['feedback'])
                    AdminReviewLog(status = tr.video_status, user = request.user, tutorial_resource = tr)
                    add_contributor_notification(tr, tut_title, 'Video is under Need Improvement state')
                    response_msg = 'Review status updated successfully!'
                except Exception, e:
                    error_msg = 'Something went wrong, please try again later.'
            else:
                error_msg = 'Invalid status code!'
    else:
        form = ReviewVideoForm()
    video_path = settings.MEDIA_ROOT + "videos/" + str(tr.tutorial_detail.foss_id) + "/" + str(tr.tutorial_detail_id) + "/" + tr.video
    video_info = get_video_info(video_path)
    if error_msg:
        messages.error(request, error_msg)
    if response_msg:
        messages.success(request, response_msg)
    context = {
        'tr': tr,
        'form': form,
        'media_url': settings.MEDIA_URL,
        'video_info': video_info,
    }
    context.update(csrf(request))
    return render(request, 'creation/templates/admin_review_video.html', context)

@login_required
def admin_reviewed_video(request):
    try:
        tr_recs = TutorialResource.objects.filter(id__in = AdminReviewLog.objects.filter(user = request.user).values_list('tutorial_resource_id').distinct())
    except:
        messages.error('Something went wrong, Please try again later.')
    context = {
        'tr_recs': tr_recs,
    }
    return render(request, 'creation/templates/admin_review_reviewed.html', context)

@login_required
def tutorials_needimprovement(request):
    if not is_contributor(request.user):
        raise PermissionDenied()
    tmp_recs = []
    con_roles = ContributorRole.objects.filter(user_id = request.user.id, status = 1)
    for rec in con_roles:
        tr_recs = TutorialResource.objects.select_related().filter(tutorial_detail_id__in = TutorialDetail.objects.filter(foss_id = rec.foss_category_id).values_list('id'), language_id = rec.language_id, status = 0).order_by('updated')
        for tr_rec in tr_recs:
            flag = 1
            if tr_rec.language.name == 'English' and tr_rec.common_content.slide_status != 5 and tr_rec.common_content.code_status != 5 and tr_rec.common_content.assignment_status != 5 and tr_rec.common_content.prerequisite_status != 5 and tr_rec.common_content.keyword_status != 5:
                flag = 0
            else:
                flag = 0
            if flag or tr_rec.outline_status == 5 or tr_rec.script_status == 5 or tr_rec.video_status == 5:
                tmp_recs.append(tr_rec)
    context = {
        'tr_recs': sorted(tmp_recs, key=lambda tutorial_resource: tutorial_resource.updated)
    }
    return render(request, 'creation/templates/my_needimprovements.html', context)

@login_required
def domain_review_index(request):
    if not is_domainreviewer(request.user):
        raise PermissionDenied()
    tmp_recs = []
    dr_roles = DomainReviewerRole.objects.filter(user_id = request.user.id, status = 1)
    for rec in dr_roles:
        tr_recs = TutorialResource.objects.select_related().filter(tutorial_detail_id__in = TutorialDetail.objects.filter(foss_id = rec.foss_category_id).values_list('id'), language_id = rec.language_id, status = 0).order_by('updated')
        for tr_rec in tr_recs:
            flag = 1
            if tr_rec.language.name == 'English' and tr_rec.common_content.slide_status != 2 and tr_rec.common_content.code_status != 2 and tr_rec.common_content.assignment_status != 2 and tr_rec.common_content.prerequisite_status != 2 and tr_rec.common_content.keyword_status != 2:
                flag = 0
            else:
                flag = 0
            if flag or tr_rec.outline_status == 2 or tr_rec.script_status == 2 or tr_rec.video_status == 2:
                tmp_recs.append(tr_rec)
    context = {
        'tr_recs': sorted(tmp_recs, key=lambda tutorial_resource: tutorial_resource.updated)
    }
    return render(request, 'creation/templates/domain_review_index.html', context)

@login_required
def domain_review_tutorial(request, trid):
    if not is_domainreviewer(request.user):
        raise PermissionDenied()
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 0)
    except:
        raise PermissionDenied()
    if DomainReviewerRole.objects.filter(user_id = request.user.id, foss_category_id = tr_rec.tutorial_detail.foss_id, language_id = tr_rec.language_id, status = 1).count() == 0:
        raise PermissionDenied()
    try:
        contrib_log = ContributorLog.objects.filter(tutorial_resource_id = tr_rec.id).order_by('-created')
        review_log = NeedImprovementLog.objects.filter(tutorial_resource_id = tr_rec.id).order_by('-created')
        review_history = DomainReviewLog.objects.filter(tutorial_resource_id = tr_rec.id).order_by('-created')
    except:
        contrib_log = None
        review_log = None
        review_history = None
    context = {
        'tr': tr_rec,
        'contrib_log': contrib_log,
        'review_log': review_log,
        'script_base': settings.SCRIPT_URL,
        'review_history': review_history
    }
    return render(request, 'creation/templates/domain_review_tutorial.html', context)

@login_required
def domain_review_component(request, trid, component):
    if not is_domainreviewer(request.user):
        raise PermissionDenied()
    try:
        tr = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        comp_title = tr.tutorial_detail.foss.foss + ': ' + tr.tutorial_detail.tutorial + ' - ' + tr.language.name
    except:
        raise PermissionDenied()
    if DomainReviewerRole.objects.filter(user_id = request.user.id, foss_category_id = tr.tutorial_detail.foss_id, language_id = tr.language_id).count() == 0:
        raise PermissionDenied()
    response_msg = ''
    error_msg = ''
    if request.method == 'POST':
        form = DomainReviewComponentForm(request.POST)
        if form.is_valid():
            if request.POST['component_status'] == '3':
                try:
                    execFlag = 0
                    if component == 'outline' or component == 'script' or component == 'video':
                        setattr(tr, component + '_status', 3)
                        tr.save()
                        execFlag = 1
                    else:
                        if tr.language.name == 'English':
                            setattr(tr.common_content, component + '_status', 3)
                            tr.common_content.save()
                            execFlag = 1
                    if execFlag:
                        DomainReviewLog.objects.create(status = 3, component = component, user = request.user, tutorial_resource = tr)
                        add_qualityreviewer_notification(tr, comp_title, component.title() + ' waiting for Quality review')
                        add_contributor_notification(tr, comp_title, component.title() + ' accepted by Domain reviewer')
                        response_msg = 'Review status updated successfully!'
                    else:
                        error_msg = 'Something went wrong, please try again later.'
                except Exception, e:
                    print e
                    error_msg = 'Something went wrong, please try again later.'
            elif request.POST['component_status'] == '5':
                try:
                    prev_state = 0
                    if component == 'outline' or component == 'script' or component == 'video':
                        prev_state = getattr(tr, component + '_status')
                        setattr(tr, component + '_status', 5)
                        tr.save()
                    else:
                        prev_state = getattr(tr.common_content, component + '_status')
                        setattr(tr.common_content, component + '_status', 5)
                        tr.common_content.save()
                    NeedImprovementLog.objects.create(user = request.user, tutorial_resource = tr, review_state = prev_state, component = component, comment = request.POST['feedback'])
                    DomainReviewLog(status = 5, component = component, user = request.user, tutorial_resource = tr)
                    add_contributor_notification(tr, comp_title, component.title() + ' is under Need Improvement state')
                    response_msg = 'Review status updated successfully!'
                except:
                    error_msg = 'Something went wrong, please try again later.'
            form = DomainReviewComponentForm()
    else:
        form = DomainReviewComponentForm()
    if error_msg:
        messages.error(request, error_msg)
    if response_msg:
        messages.success(request, response_msg)
    context = {
        'form': form,
        'tr': tr,
        'component': component,
    }

    return render(request, 'creation/templates/domain_review_component.html', context)

@login_required
def domain_reviewed_tutorials(request):
    try:
        tr_recs = TutorialResource.objects.filter(id__in = DomainReviewLog.objects.filter(user = request.user).values_list('tutorial_resource_id').distinct())
    except:
        messages.error('Something went wrong, Please try again later.')
    context = {
        'tr_recs': tr_recs,
    }
    return render(request, 'creation/templates/domain_review_reviewed.html', context)

def accept_all(request, review, trid):
    status_flag = {
        'domain': 3,
        'quality': 4
    }
    flag = 0
    if not is_domainreviewer(request.user):
        raise PermissionDenied()
    try:
        tr = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        comp_title = tr.tutorial_detail.foss.foss + ': ' + tr.tutorial_detail.tutorial + ' - ' + tr.language.name
    except:
        raise PermissionDenied()
    if DomainReviewerRole.objects.filter(user_id = request.user.id, foss_category_id = tr.tutorial_detail.foss_id, language_id = tr.language_id).count() == 0:
        raise PermissionDenied()
    if review in status_flag:
        current_status = status_flag[review] - 1
    else:
        raise PermissionDenied()
    comp_message = ''
    if tr.outline_status > 0 and tr.outline_status == current_status:
        tr.outline_status = status_flag[review]
        if review == 'quality':
            QualityReviewLog.objects.create(status = status_flag[review], component = 'outline', user = request.user, tutorial_resource = tr)
            comp_message = 'Outline accepted by Quality reviewer'
        else:
            DomainReviewLog.objects.create(status = status_flag[review], component = 'outline', user = request.user, tutorial_resource = tr)
            add_qualityreviewer_notification(tr, comp_title, 'Outline waiting for Quality review')
            comp_message = 'Outline accepted by Domain reviewer'
        add_contributor_notification(tr, comp_title, comp_message)
        flag = 1

    if tr.script_status > 0 and tr.script_status == current_status:
        tr.script_status = status_flag[review]
        if review == 'quality':
            QualityReviewLog.objects.create(status = status_flag[review], component = 'script', user = request.user, tutorial_resource = tr)
            comp_message = 'Script accepted by Quality reviewer'
        else:
            DomainReviewLog.objects.create(status = status_flag[review], component = 'script', user = request.user, tutorial_resource = tr)
            add_qualityreviewer_notification(tr, comp_title, 'Script waiting for Quality review')
            comp_message = 'Script accepted by Domain reviewer'
        add_contributor_notification(tr, comp_title, comp_message)
        flag = 1

    if tr.video_status > 0 and tr.video_status == current_status:
        tr.video_status = status_flag[review]
        if review == 'quality':
            QualityReviewLog.objects.create(status = status_flag[review], component = 'video', user = request.user, tutorial_resource = tr)
            comp_message = 'Video accepted by Quality reviewer'
        else:
            DomainReviewLog.objects.create(status = status_flag[review], component = 'video', user = request.user, tutorial_resource = tr)
            add_qualityreviewer_notification(tr, comp_title, 'Video waiting for Quality review')
            comp_message = 'Video accepted by Domain reviewer'
        add_contributor_notification(tr, comp_title, comp_message)
        flag = 1
    tr.save()

    if tr.language.name == 'English':
        if tr.common_content.slide_status > 0 and tr.common_content.slide_status == current_status:
            tr.common_content.slide_status = status_flag[review]
            if review == 'quality':
                QualityReviewLog.objects.create(status = status_flag[review], component = 'slide', user = request.user, tutorial_resource = tr)
                comp_message = 'Slide accepted by Quality reviewer'
            else:
                DomainReviewLog.objects.create(status = status_flag[review], component = 'slide', user = request.user, tutorial_resource = tr)
                add_qualityreviewer_notification(tr, comp_title, 'Slide waiting for Quality review')
                comp_message = 'Slide accepted by Domain reviewer'
            add_contributor_notification(tr, comp_title, comp_message)
            flag = 1

        if tr.common_content.code_status > 0 and tr.common_content.code_status == current_status:
            tr.common_content.code_status = status_flag[review]
            if review == 'quality':
                QualityReviewLog.objects.create(status = status_flag[review], component = 'code', user = request.user, tutorial_resource = tr)
                comp_message = 'Codefiles accepted by Quality reviewer'
            else:
                DomainReviewLog.objects.create(status = status_flag[review], component = 'code', user = request.user, tutorial_resource = tr)
                add_qualityreviewer_notification(tr, comp_title, 'Codefiles waiting for Quality review')
                comp_message = 'Codefiles accepted by Domain reviewer'
            add_contributor_notification(tr, comp_title, comp_message)
            flag = 1

        if tr.common_content.assignment_status > 0 and tr.common_content.assignment_status == current_status:
            tr.common_content.assignment_status = status_flag[review]
            if review == 'quality':
                QualityReviewLog.objects.create(status = status_flag[review], component = 'assignment', user = request.user, tutorial_resource = tr)
                comp_message = 'Assignment accepted by Quality reviewer'
            else:
                DomainReviewLog.objects.create(status = status_flag[review], component = 'assignment', user = request.user, tutorial_resource = tr)
                add_qualityreviewer_notification(tr, comp_title, 'Assignment waiting for Quality review')
                comp_message = 'Assignment accepted by Domain reviewer'
            add_contributor_notification(tr, comp_title, comp_message)
            flag = 1

        if tr.common_content.prerequisite_status > 0 and tr.common_content.prerequisite_status == current_status:
            tr.common_content.prerequisite_status = status_flag[review]
            if review == 'quality':
                QualityReviewLog.objects.create(status = status_flag[review], component = 'prerequisite', user = request.user, tutorial_resource = tr)
                comp_message = 'Prerequisite accepted by Quality reviewer'
            else:
                DomainReviewLog.objects.create(status = status_flag[review], component = 'prerequisite', user = request.user, tutorial_resource = tr)
                add_qualityreviewer_notification(tr, comp_title, 'Prerequisite waiting for Quality review')
                comp_message = 'Prerequisite accepted by Domain reviewer'
            add_contributor_notification(tr, comp_title, comp_message)
            flag = 1

        if tr.common_content.keyword_status > 0 and tr.common_content.keyword_status == current_status:
            tr.common_content.keyword_status = status_flag[review]
            if review == 'quality':
                QualityReviewLog.objects.create(status = status_flag[review], component = 'keyword', user = request.user, tutorial_resource = tr)
                comp_message = 'Keywords accepted by Quality reviewer'
            else:
                DomainReviewLog.objects.create(status = status_flag[review], component = 'keyword', user = request.user, tutorial_resource = tr)
                add_qualityreviewer_notification(tr, comp_title, 'Keywords waiting for Quality review')
                comp_message = 'Keywords accepted by Domain reviewer'
            add_contributor_notification(tr, comp_title, comp_message)
            flag = 1

        tr.common_content.save()
    if not flag:
        messages.warning(request, 'There is no component available for Domain reviewr to accept.')

    return HttpResponseRedirect('/creation/' + review + '-review/tutorial/' + str(tr.id) + '/')

@login_required
def quality_review_index(request, tabid = 1):
    if not is_qualityreviewer(request.user):
        raise PermissionDenied()
    tmp_recs = []
    com_recs = []
    pub_recs = []
    qr_roles =  QualityReviewerRole.objects.filter(user_id = request.user.id, status = 1)
    for rec in qr_roles:
        tr_recs = TutorialResource.objects.select_related().filter(tutorial_detail_id__in = TutorialDetail.objects.filter(foss_id = rec.foss_category_id).values_list('id'), language_id = rec.language_id, status = 0).order_by('updated')
        for tr_rec in tr_recs:
            if tr_rec.outline_status == 3 or tr_rec.script_status == 3 or tr_rec.video_status == 3:
                tmp_recs.append(tr_rec)
            elif tr_rec.language.name == 'English' and (tr_rec.common_content.slide_status == 3 or tr_rec.common_content.code_status == 3 or tr_rec.common_content.assignment_status == 3 or tr_rec.common_content.keyword_status == 3  or tr_rec.common_content.prerequisite_status == 3):
                tmp_recs.append(tr_rec)
            else:
                flag = 0
                if tr_rec.language.name == 'English':
                    if tr_rec.common_content.slide_status == 4 and (tr_rec.common_content.code_status == 4 or tr_rec.common_content.code_status == 6) and (tr_rec.common_content.assignment_status == 4 or tr_rec.common_content.assignment_status == 6) and tr_rec.common_content.keyword_status == 4 and (tr_rec.common_content.prerequisite_status == 4 or tr_rec.common_content.prerequisite_status == 6):
                        flag = 1
                else:
                    flag = 1
                if flag and tr_rec.outline_status == 4 and tr_rec.script_status == 4 and tr_rec.video_status == 4:
                    com_recs.append(tr_rec)
            if tr_rec.language.name != 'English' and (tr_rec.outline_status > 0 and tr_rec.outline_status != 5) and (tr_rec.script_status > 0 and tr_rec.script_status != 5) and (tr_rec.video_status > 0 and tr_rec.video_status != 5):
                pub_recs.append(tr_rec)

    context = {
        'tabid': str(tabid),
        'tr_recs': sorted(tmp_recs, key=lambda tutorial_resource: tutorial_resource.updated),
        'com_recs': sorted(com_recs, key=lambda tutorial_resource: tutorial_resource.updated),
        'pub_recs': sorted(pub_recs, key=lambda tutorial_resource: tutorial_resource.updated),
    }
    return render(request, 'creation/templates/quality_review_index.html', context)

@login_required
def public_review_list(request):
    if not is_qualityreviewer(request.user):
        raise PermissionDenied()
    pub_recs = []
    qr_roles =  QualityReviewerRole.objects.filter(user_id = request.user.id, status = 1)
    for rec in qr_roles:
        tr_recs = TutorialResource.objects.select_related().filter(tutorial_detail_id__in = TutorialDetail.objects.filter(foss_id = rec.foss_category_id).values_list('id'), language_id = rec.language_id, status = 2).order_by('updated')
        for tr_rec in tr_recs:
            pub_recs.append(tr_rec)
    context = {
        'pubrev_recs': pub_recs
    }
    return render(request, 'creation/templates/public_review_list.html', context)

@login_required
def public_review_publish(request, trid):
    if not is_qualityreviewer(request.user):
        raise PermissionDenied()
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 2)
        comp_title = tr_rec.tutorial_detail.foss.foss + ': ' + tr_rec.tutorial_detail.tutorial + ' - ' + tr_rec.language.name
    except:
        raise PermissionDenied()
    if QualityReviewerRole.objects.filter(user = request.user, foss_category = tr_rec.tutorial_detail.foss).count() == 0:
        raise PermissionDenied()
    flag = 1
    if tr_rec.language.name == 'English':
        if tr_rec.common_content.slide_status > 0 and tr_rec.common_content.code_status > 0 and tr_rec.common_content.assignment_status > 0 and tr_rec.common_content.prerequisite_status > 0 and tr_rec.common_content.keyword_status > 0:
            if tr_rec.common_content.slide_status != 6:
                tr_rec.common_content.slide_status = 4
            if tr_rec.common_content.code_status != 6:
                tr_rec.common_content.code_status = 4
            if tr_rec.common_content.assignment_status != 6:
                tr_rec.common_content.assignment_status = 4
            if tr_rec.common_content.prerequisite_status != 6:
                tr_rec.common_content.prerequisite_status = 4
            tr_rec.common_content.keyword_status = 4
        else:
            flag = 0
    if flag and tr_rec.outline_status > 0 and tr_rec.script_status > 0 and tr_rec.video_status > 0:
        tr_rec.outline_status = 4
        tr_rec.script_status = 4
        tr_rec.video_status = 4
    else:
        flag = 0
    if flag:
        if tr_rec.language.name == 'English':
            tr_rec.common_content.save()
        tr_rec.status = 1
        tr_rec.save()
        add_contributor_notification(tr_rec, comp_title, 'This tutorial is published now.')
        messages.success(request, 'Selected tutorial published successfully!')
    else:
        messages.error('Some components are missing, upload those missing components to publish')
    return HttpResponseRedirect('/creation/public-review/list/')

@login_required
def public_review_mark_as_pending(request, trid):
    if not is_qualityreviewer(request.user):
        raise PermissionDenied()
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 2)
        comp_title = tr_rec.tutorial_detail.foss.foss + ': ' + tr_rec.tutorial_detail.tutorial + ' - ' + tr_rec.language.name
    except:
        raise PermissionDenied()
    if QualityReviewerRole.objects.filter(user = request.user, foss_category = tr_rec.tutorial_detail.foss).count() == 0:
        raise PermissionDenied()
    if tr_rec.language.name == 'English':
        if tr_rec.common_content.slide_status > 0 and tr_rec.common_content.slide_status != 6:
            tr_rec.common_content.slide_status = 2
        if tr_rec.common_content.code_status > 0 and tr_rec.common_content.code_status != 6:
            tr_rec.common_content.code_status = 4
        if tr_rec.common_content.assignment_status > 0 and tr_rec.common_content.assignment_status != 6:
            tr_rec.common_content.assignment_status = 4
        if tr_rec.common_content.prerequisite_status > 0 and tr_rec.common_content.prerequisite_status != 6:
            tr_rec.common_content.prerequisite_status = 4
        if tr_rec.common_content.keyword_status > 0:
            tr_rec.common_content.keyword_status = 2
    if tr_rec.outline_status > 0:
        tr_rec.outline_status = 2
    if tr_rec.script_status > 0:
        tr_rec.script_status = 2
    if tr_rec.video_status > 0:
        tr_rec.video_status = 2
    try:
        tr_rec.common_content.save()
        tr_rec.status = 0
        tr_rec.save()
        add_contributor_notification(tr_rec, comp_title, 'This tutorial moved from public review to regular review process.')
        messages.success(request, 'Selected tutorial is marked as pending.')
    except Exception, e:
        messages.error(request, str(e))

    return HttpResponseRedirect('/creation/public-review/list/')

@login_required
def quality_review_tutorial(request, trid):
    if not is_qualityreviewer(request.user):
        raise PermissionDenied()
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 0)
    except:
        raise PermissionDenied()
    if QualityReviewerRole.objects.filter(user_id = request.user.id, foss_category_id = tr_rec.tutorial_detail.foss_id, language_id = tr_rec.language_id, status = 1).count() == 0:
        raise PermissionDenied()
    try:
        contrib_log = ContributorLog.objects.filter(tutorial_resource_id = tr_rec.id).order_by('-created')
        review_log = NeedImprovementLog.objects.filter(tutorial_resource_id = tr_rec.id).order_by('-created')
        review_history = QualityReviewLog.objects.filter(tutorial_resource_id = tr_rec.id).order_by('-created')
    except:
        contrib_log = None
        review_log = None
        review_history = None
    context = {
        'tr': tr_rec,
        'contrib_log': contrib_log,
        'review_log': review_log,
        'review_history': review_history,
        'script_base': settings.SCRIPT_URL,
    }
    return render(request, 'creation/templates/quality_review_tutorial.html', context)

@login_required
def quality_review_component(request, trid, component):
    if not is_qualityreviewer(request.user):
        raise PermissionDenied()
    try:
        tr = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        comp_title = tr.tutorial_detail.foss.foss + ': ' + tr.tutorial_detail.tutorial + ' - ' + tr.language.name
    except:
        raise PermissionDenied()
    if QualityReviewerRole.objects.filter(user_id = request.user.id, foss_category_id = tr.tutorial_detail.foss_id, language_id = tr.language_id, status = 1).count() == 0:
        raise PermissionDenied()
    response_msg = ''
    error_msg = ''
    if request.method == 'POST':
        form = QualityReviewComponentForm(request.POST)
        if form.is_valid():
            if request.POST['component_status'] == '4':
                try:
                    execFlag = 0
                    if component == 'outline' or component == 'script' or component == 'video':
                        setattr(tr, component + '_status', 4)
                        tr.save()
                        execFlag = 1
                    else:
                        if tr.language.name == 'English':
                            setattr(tr.common_content, component + '_status', 4)
                            tr.common_content.save()
                            execFlag = 1
                    if execFlag:
                        comp_message = component.title() + ' accepted by Quality reviewer'
                        QualityReviewLog.objects.create(status = 4, component = component, user = request.user, tutorial_resource = tr)
                        add_contributor_notification(tr, comp_title, comp_message)
                        response_msg = 'Review status updated successfully!'
                    else:
                        error_msg = 'Something went wrong, please try again later.'
                except Exception, e:
                    error_msg = 'Something went wrong, please try again later.'
            elif request.POST['component_status'] == '5':
                try:
                    prev_state = 0
                    execFlag = 0
                    if component == 'outline' or component == 'script' or component == 'video':
                        prev_state = getattr(tr, component + '_status')
                        setattr(tr, component + '_status', 5)
                        tr.save()
                        execFlag = 1
                    else:
                        if tr.language.name == 'English':
                            prev_state = getattr(tr.common_content, component + '_status')
                            setattr(tr.common_content, component + '_status', 5)
                            tr.common_content.save()
                            execFlag = 1
                    if execFlag:
                        NeedImprovementLog.objects.create(user = request.user, tutorial_resource = tr, review_state = prev_state, component = component, comment = request.POST['feedback'])
                        comp_message = component.title() + ' is under Need Improvement state'
                        QualityReviewLog.objects.create(status = 5, component = component, user = request.user, tutorial_resource = tr)
                        add_contributor_notification(tr, comp_title, comp_message)
                        response_msg = 'Review status updated successfully!'
                    else:
                        error_msg = 'Something went wrong, please try again later.'
                except:
                    error_msg = 'Something went wrong, please try again later.'
            form = QualityReviewComponentForm()
    else:
        form = QualityReviewComponentForm()
    if error_msg:
        messages.error(request, error_msg)
    if response_msg:
        messages.success(request, response_msg)
    context = {
        'form': form,
        'tr': tr,
        'component': component,
    }

    return render(request, 'creation/templates/quality_review_component.html', context)

@login_required
def public_review_tutorial(request, trid):
    if not is_qualityreviewer(request.user):
        raise PermissionDenied()
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        comp_title = tr_rec.tutorial_detail.foss.foss + ': ' + tr_rec.tutorial_detail.tutorial + ' - ' + tr_rec.language.name
    except:
        raise PermissionDenied()
    if QualityReviewerRole.objects.filter(user_id = request.user.id, foss_category_id = tr_rec.tutorial_detail.foss_id, language_id = tr_rec.language_id, status = 1).count() == 0:
        raise PermissionDenied()
    if tr_rec.language.name != 'English' and (tr_rec.outline_status > 0 and tr_rec.outline_status != 5) and (tr_rec.script_status > 0 and tr_rec.script_status != 5) and (tr_rec.video_status > 0 and tr_rec.video_status != 5):
        tr_rec.status = 2
        tr_rec.save()
        PublicReviewLog.objects.create(user = request.user, tutorial_resource = tr_rec)
        add_contributor_notification(tr_rec, comp_title, 'This tutorial is now available for Public review')
        messages.success(request, 'The selected tutorial is now available for Public review')
    else:
        messages.error(request, 'The selected tutorial cannot be marked as Public review')
    return HttpResponseRedirect('/creation/quality-review/2/')

@login_required
def publish_tutorial(request, trid):
    if not is_qualityreviewer(request.user):
        raise PermissionDenied()
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid, status = 0)
        comp_title = tr_rec.tutorial_detail.foss.foss + ': ' + tr_rec.tutorial_detail.tutorial + ' - ' + tr_rec.language.name
    except:
        raise PermissionDenied()
    if QualityReviewerRole.objects.filter(user_id = request.user.id, foss_category_id = tr_rec.tutorial_detail.foss_id, language_id = tr_rec.language_id, status = 1).count() == 0:
        raise PermissionDenied()
    flag = 0
    if tr_rec.language.name == 'English':
        if tr_rec.common_content.slide_status == 4 and (tr_rec.common_content.code_status == 4 or tr_rec.common_content.code_status == 6) and (tr_rec.common_content.assignment_status == 4 or tr_rec.common_content.assignment_status == 6) and tr_rec.common_content.keyword_status == 4 and (tr_rec.common_content.prerequisite_status == 4 or tr_rec.common_content.prerequisite_status == 6):
            flag = 1
    else:
        flag = 1
    if flag and tr_rec.outline_status == 4 and tr_rec.script_status == 4 and tr_rec.video_status == 4:
        tr_rec.status = 1
        tr_rec.save()
        PublishTutorialLog.objects.create(user = request.user, tutorial_resource = tr_rec)
        add_contributor_notification(tr_rec, comp_title, 'This tutorial is published now')
        messages.success(request, 'The selected tutorial is published successfully')
    else:
        messages.error(request, 'The selected tutorial cannot be marked as Public review')
    return HttpResponseRedirect('/creation/quality-review/3/')

@login_required
def quality_reviewed_tutorials(request):
    try:
        tr_recs = TutorialResource.objects.filter(id__in = QualityReviewLog.objects.filter(user = request.user).values_list('tutorial_resource_id').distinct())
    except:
        messages.error('Something went wrong, Please try again later.')
    context = {
        'tr_recs': tr_recs,
    }
    return render(request, 'creation/templates/quality_review_reviewed.html', context)

@login_required
def delete_creation_notification(request, notif_type, notif_id):
    notif_rec = None
    try:
        if notif_type == "contributor":
            notif_rec = ContributorNotification.objects.select_related().get(pk = notif_id, user = request.user)
        elif notif_type == "admin":
            notif_rec = AdminReviewerNotification.objects.select_related().get(pk = notif_id, user = request.user)
        elif notif_type == "domain":
            notif_rec = DomainReviewerNotification.objects.select_related().get(pk = notif_id, user = request.user)
        elif notif_type == "quality":
            notif_rec = QualityReviewerNotification.objects.select_related().get(pk = notif_id, user = request.user)
    except:
        messages.warning(request, 'Selected notification is already deleted (or) You do not have permission to delete it.')
    if notif_rec and notif_rec.user.id == request.user.id:
        notif_rec.delete()
    return HttpResponseRedirect(request.META['HTTP_REFERER'])

@login_required
def clear_creation_notification(request, notif_type):
    notif_rec = None
    try:
        if notif_type == "contributor":
            notif_rec = ContributorNotification.objects.filter(user = request.user).delete()
        elif notif_type == "admin":
            notif_rec = AdminReviewerNotification.objects.filter(user = request.user).delete()
        elif notif_type == "domain":
            notif_rec = DomainReviewerNotification.objects.filter(user = request.user).delete()
        elif notif_type == "quality":
            notif_rec = QualityReviewerNotification.objects.filter(user = request.user).delete()
    except:
        messages.warning(request, 'Something went wrong, contact site administrator.')

    return HttpResponseRedirect(request.META['HTTP_REFERER'])

def creation_view_tutorial(request, trid):
    try:
        tr_rec = TutorialResource.objects.select_related().get(pk = trid)
        tr_recs = TutorialResource.objects.select_related().filter(tutorial_detail__in = TutorialDetail.objects.filter(foss = tr_rec.tutorial_detail.foss).order_by('order').values_list('id'), language = tr_rec.language)
    except Exception, e:
        messages.error(request, str(e))
    video_path = settings.MEDIA_ROOT + "videos/" + str(tr_rec.tutorial_detail.foss_id) + "/" + str(tr_rec.tutorial_detail_id) + "/" + tr_rec.video
    video_info = get_video_info(video_path)
    context = {
        'tr_rec': tr_rec,
        'tr_recs': sorted(tr_recs, key=lambda tutorial_resource: tutorial_resource.tutorial_detail.order),
        'video_info': video_info,
        'media_url': settings.MEDIA_URL,
        'script_base': settings.SCRIPT_URL
    }
    return render(request, 'creation/templates/creation_view_tutorial.html', context)
