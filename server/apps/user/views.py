from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
from django.shortcuts import render, HttpResponse, redirect
from django.views.decorators.http import require_http_methods
from django.http import FileResponse
from .models import Teacher, Student
from utils.VertificationUtil import VertificationCode
from utils.EmailUtil import EmailUtil
from utils.FileUtil import handle_user_excel, write_file
from server.settings import RESOURCES_DIR
from apps.record.models import *
import json
import os
import time
import base64
import datetime
# Create your views here.


try:
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    @register_job(scheduler, 'cron', day_of_week='sat', hour='8', minute='00', second='00', id='remove_overdue_record')
    def remove_overdue_record():
        td = datetime.date.today()
        overdue = datetime.datetime(td.year, td.month - 1, td.day, 8, 0, 0)
        loginrecords = LoginRecord.objects.filter(time__lt=overdue)
        loginrecords.delete()
        certifyrecords = EmailCertificationRecord.objects.filter(time__lt=overdue)
        certifyrecords.delete()
        changepwdrecords = ChangePasswordRecord.objects.filter(time__lt=overdue)
        changepwdrecords.delete()
        certifysentrecords = CertificationSentRecord.objects.filter(time__lt=overdue)
        certifysentrecords.delete()
        verifysent = VerifyCodeSentRecord.objects.filter(time__lt=overdue)
        verifysent.delete()
    register_events(scheduler)
    scheduler.start()
except Exception as e:
    print(e)
    scheduler.shutdown()


def index(request):
    is_login, user = check_is_login(request)
    if is_login == 1:
        if len(user.email) == 0:
            return redirect("/user/email/certificate")
        return render(request, 'user/index.html', {"user": user})
    elif is_login == 0:
        return redirect("/user/login")
    return HttpResponse(status=500)


def login(request):
    if request.method == 'GET':
        if request.session.get('account'):
            return redirect("/user/index")
        return render(request, 'user/login.html')
    if request.method == 'POST':
        u_account = request.POST.get('account')
        u_password = request.POST.get('password')
        u_identity = request.POST.get('identity')
        u_code = request.POST.get('verify_code')
        if u_code.upper() != request.session.get('verify_code').upper():
            msg = 'wrong verification code'
            return render(request, 'user/login.html', {'message': msg})
        if u_identity == '1':
            user = Teacher.objects.filter(account=u_account)
        elif u_identity == '2':
            user = Student.objects.filter(account=u_account)
        else:
            return HttpResponse(status=500)
        if len(user) == 1:
            if user[0].password == u_password:
                user[0].save()
                request.session['account'] = user[0].account
                request.session['identity'] = user[0].identity
                record = LoginRecord(account=user[0].account,
                                     identity=user[0].identity,
                                     success=True)
                record.save()
                return redirect('/user/index')
            msg = 'wrong password'
            return render(request, 'user/login.html', {'message': msg})
        if len(user) == 0:
            msg = '\'{}\' does not exist'.format(u_account)
            return render(request, 'user/login.html', {'message': msg})
        return HttpResponse(status=500)
    return HttpResponse(status=405)


def get_verify_code(request):
    generator = VertificationCode()
    verify_code, verify_img = generator.get_code_image()
    request.session['verify_code'] = verify_code
    return HttpResponse(verify_img)


def logout(request):
    is_login, user = check_is_login(request)
    if is_login == 0:
        return redirect("/user/login")
    request.session.flush()
    return redirect('/user/login')


def certificate_email(request):
    if request.method == 'GET':
        is_login, user = check_is_login(request)
        if is_login == 0:
            return redirect("/user/login")
        return render(request, 'user/certificateEmail.html', {})
    elif request.method == 'POST':
        email = request.POST.get('email')
        recipients = [email]
        account = request.session.get('account')
        identity = request.session.get('identity')
        manager = EmailUtil(account, identity, recipients)
        result = manager.send(email_type='certificate')
        if result == 1:
            msg = "认证邮件已发送"
        else:
            msg = "邮件发送失败"
        return render(request, 'user/certificateEmail.html', {"message": msg})
    return HttpResponse(status=405)


@require_http_methods(["GET"])
def active_email(request):
    active_code = request.GET.get("code")
    token = request.GET.get("token")
    obj = CertificationSentRecord.objects.filter(active_code=active_code, token=token)
    if len(obj) == 1:
        email = str(obj[0].recipients).split(';')[0]
        account = obj[0].account
        identity = obj[0].identity
        user = get_user_by_account(account, identity)
        user.email = email
        record = EmailCertificationRecord(account=account, identity=identity, email=email, success=True)
        user.save()
        record.save()
        return redirect("/user/index")
    return HttpResponse(status=500)


def change_password(request):
    if request.method == 'GET':
        is_login, user = check_is_login(request)
        if is_login == 0:
            return redirect("/user/login")
        return render(request, 'user/changePassword.html', {})
    if request.method == 'POST':
        user = get_user_from_request(request)
        old_pwd = request.POST.get('old_password')
        new_pwd = request.POST.get('new_password')
        if old_pwd == user.password:
            user.password = new_pwd
            record = ChangePasswordRecord(
                old_password=old_pwd,
                new_password=new_pwd,
                account=user.account,
                identity=user.identity,
                success=True
            )
            user.save()
            record.save()
            request.session.flush()
            return redirect('/user/login')
        return render(request, 'user/changePassword.html', {"message": "用户密码错误"})
    return HttpResponse(status=405)


def forgot_password(request):
    if request.method == 'GET':
        if request.GET.get("account"):
            account = request.GET.get("account")
            identity = request.GET.get("identity")
            code = request.GET.get("code")
            obj = VerifyCodeSentRecord.objects.filter(account=account, identity=identity, code=code)
            if len(obj) != 0:
                if code == obj[len(obj) - 1].code:
                    request.session['account'] = account
                    request.session['identity'] = identity
                    return render(request, 'user/forgotPassword.html', {"step": 2})
                return HttpResponse(status=500)
            return HttpResponse(status=500)
        return render(request, 'user/forgotPassword.html', {"step": 1})
    if request.method == 'POST':
        pwd = request.POST.get("reset_password")
        user = get_user_from_request(request)
        if not user:
            return HttpResponse(status=500)
        record = ChangePasswordRecord(
            account=user.account,
            identity=user.identity,
            old_password=user.password,
            new_password=pwd,
            success=True,
            ext="forgot password"
        )
        record.save()
        user.password = pwd
        user.save()
        request.session.flush()
        return redirect('/user/login')
    return HttpResponse(status=405)


def check_is_login(request):
    if request.session.get("account"):
        account = request.session['account']
        identity = request.session['identity']
        if identity == '1':
            user = Teacher.objects.filter(account=account)
        elif identity == '2':
            user = Student.objects.filter(account=account)
        else:
            return -3, None
        if len(user) == 1:
            return 1, user[0]
        elif len(user) == 0:
            return -1, None
        else:
            return -2, None
    return 0, None


def get_user_by_account(account, identity):
    if identity == '1':
        result = Teacher.objects.filter(account=account)
    elif identity == '2':
        result = Student.objects.filter(account=account)
    else:
        return None
    if len(result) == 1:
        return result[0]
    return None


def get_user_from_request(request):
    account = request.session.get("account")
    identity = request.session.get("identity")
    if account and identity:
        return get_user_by_account(account, identity)
    return None


def send_verify_code(request):
    account = request.GET.get("account")
    email = request.GET.get("email")
    identity = request.GET.get("identity")
    user = get_user_by_account(account, identity)
    if not user:
        return HttpResponse(json.dumps({"data": "not exist"}))
    if email != user.email:
        return HttpResponse(json.dumps({"data": "not match"}))
    if "" == user.email:
        return HttpResponse(json.dumps({"data": "no email"}))
    manager = EmailUtil(account=account, identity=identity, receive=[email])
    result = manager.send('forgot')
    if 1 != result:
        return HttpResponse(json.dumps({"data": "failed"}))
    return HttpResponse(json.dumps({"data": "sent"}))


@require_http_methods(['GET'])
def import_user(request):
    return render(request, "user/import_user.html")


def import_user_save(request, identity):
    if request.method == 'POST':
        if identity == 1:
            tec_file = request.FILES.get("teacher_excel")
            filename = 'teachers_' + str(time.time()).replace('.', '') + '.xls'
            saved_path = os.path.join(RESOURCES_DIR, 'user', filename)
            write_file(tec_file, saved_path)
            tec_data = handle_user_excel(saved_path)
            for t in tec_data:
                account = str(t["account"])
                pwd = account[len(account) - 6: len(account)]
                teacher = Teacher(
                    account=account,
                    real_name=t["name"],
                    email="",
                    password=base64.b64encode(pwd.encode('utf-8')).decode("utf-8")
                )
                teacher.save()
        if identity == 2:
            stu_file = request.FILES.get("student_excel")
            filename = 'students_' + str(time.time()).replace('.', '') + '.xls'
            saved_path = os.path.join(RESOURCES_DIR, 'user', filename)
            write_file(stu_file, saved_path)
            stu_data = handle_user_excel(saved_path)
            for s in stu_data:
                account = str(s["account"])
                pwd = account[len(account) - 6: len(account)]
                student = Student(
                    account=account,
                    real_name=s["name"],
                    email="",
                    password=base64.b64encode(pwd.encode('utf-8')).decode("utf-8")
                )
                student.save()
        request.session['msg'] = "import successfully."
        return redirect("/user/import")


@require_http_methods(['GET'])
def download_student(request):
    return temp_download('student.xls')


@require_http_methods(['GET'])
def download_teacher(request):
    return temp_download('teacher.xls')


def temp_download(filename):
    temp_path = os.path.join(RESOURCES_DIR, 'user', filename)
    f = open(temp_path, 'rb')
    response = FileResponse(f)
    response["Content-Type"] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="' + filename + '"'
    return response
