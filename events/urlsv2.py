# urls.py
from django.conf.urls import url
from events.viewsv2 import *
from events.decorators import *
from events.formsv2 import *
urlpatterns = [
    url(
      r'^training-planner/', 
      TrainingPlannerListView.as_view(template_name="training_planner.html"), 
      name="training_planner"
    ),
    url(
      r'^student-batch/new/$', 
      StudentBatchCreateView.as_view(template_name="new_batch.html", \
        form_class=StudentBatchForm), 
      name="add_batch"
    ),
    url(
      r'^student-batch/(?P<bid>\d+)/new/$', 
      StudentBatchCreateView.as_view(template_name="update_batch.html", \
        form_class=NewStudentBatchForm), 
      name="add_student"
    ),
    url(
      r'^student-batch/(?P<pk>\d+)/$', 
      StudentBatchUpdateView.as_view(template_name="edit_batch.html", \
        form_class=UpdateStudentBatchForm), 
      name="edit_student"
    ),
    url(
      r'^student-batch/(?P<bid>\d+)/view/$', 
      StudentListView.as_view(template_name="list_student.html"), 
      name="list_student"
    ),
    url(
      r'^student-batch/$', 
      StudentBatchListView.as_view(template_name="student_batch_list.html"), 
      name="batch_list"
    ),
    url(
      r'^(?P<tpid>\d+)/training-request', 
      TrainingRequestCreateView.as_view(template_name="training_request.html"), 
      name="training_request"
    ),
    url(
      r'^(?P<tid>\d+)/attendance', 
      TrainingAttendanceListView.as_view(template_name=\
        "training_attendance.html"), 
      name="training_attendance"
    ),
    url(
      r'^training-request/(?P<trid>\d+)/$', 
      TrainingRequestEditView.as_view(template_name=\
        "edit_training_request.html"), 
      name="edit_training_request"
    ),
    url(
      r'^(?P<bid>\d+)/student-delete/(?P<pk>\d+)/$', 
      StudentDeleteView.as_view(template_name="student_delete.html", \
        success_url="/software-training/student-batch"), 
      name="student_delete"
    ),
    url(
      r'^training-certificate/(?P<taid>\d+)/organiser/$', 
      OrganiserTrainingCertificateView.as_view(), \
        name="organiser_training_certificate"
    ),
    url(
      r'^training-certificate/(?P<taid>\d+)/student/$', 
      StudentTrainingCertificateView.as_view(), \
        name="student_training_certificate"
    ),
    url(
      r'^course-map/$', 
      CourseMapCreateView.as_view(template_name=\
        "coursemap.html"), 
      name="coursemap"
    ),
    url(
      r'^course-map-list/$', 
      CourseMapListView.as_view(template_name="coursemap_list.html"), 
      name="coursemaplist"
    ),
    url(
      r'^course-map/(?P<pk>\d+)$', 
      CourseMapUpdateView.as_view(template_name=\
        "coursemap.html"), 
      name="coursemapupdate"
    ),
    url(
      r'^single-training/approved/$', 
     SingletrainingApprovedListView.as_view(template_name="single-training.html"), 
      name="single-training-approved"
    ),
    url(
      r'^single-training/completed/$', 
     SingletrainingCompletedListView.as_view(template_name="single-training.html"), 
      name="single-training-completed"
    ),
    url(
      r'^single-training/new/$', 
     SingletrainingCreateView.as_view(template_name="single-training-form.html"), 
      name="new-single-training"
    ),
    #ajax
    url(
      r'^save-student/', 
      SaveStudentView.as_view()
    ),
    url(
      r'^get-course-option/', 
      GetCourseOptionView.as_view()
    ),
    url(
      r'^get-batch-option/', 
      GetBatchOptionView.as_view()
    ),
    url(
      r'^get-batch-course-status/', 
      GetBatchStatusView.as_view()
    ),
    url(
      r'^training-request/(?P<role>\w+)/(?P<status>\w+)/$', 
      TrainingRequestListView.as_view(template_name='training_list.html'), 
      name='training_list'
    ),
    #url(r'^get-language-option/', GetLanguageOptionView.as_view()),
    #For Sample Calender Add/Delete/View
    url(
      r'^sample-calender/new/$',
      SampleCalenderCreateView.as_view(template_name=\
        "sample_calender.html"),
      name="sample_calender_new"
    ),
    url(
      r'^sample-calender/$',
      SampleCalenderListView.as_view(template_name=\
        "sample_calender_list.html"),
      name="sample_calender_list"
    ),
    url(
      r'^sample-calender/delete/(?P<pk>\d+)$',
      SampleCalenderDeleteView.as_view(template_name=\
        "student_delete.html", \
        success_url="/software-training/sample-calender/"),
      name="sample_calender_delete"
    ),
]
