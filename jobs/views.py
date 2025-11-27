# jobs/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db.models import Q
from .forms import UserRegisterForm, JobForm, ApplicationForm
from .models import Job, Application
from django.urls import reverse
from django.contrib.auth.views import LogoutView


def home(request):
    return render(request, 'jobs/home.html')

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data.pop('role')
            user = form.save()
            # create groups if not exist
            employer_group, _ = Group.objects.get_or_create(name='Employer')
            applicant_group, _ = Group.objects.get_or_create(name='Applicant')
            if role == 'employer':
                user.groups.add(employer_group)
            else:
                user.groups.add(applicant_group)
            username = form.cleaned_data.get('username')
            # automatically login
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserRegisterForm()
    return render(request, 'jobs/register.html', {'form': form})

@login_required
def dashboard(request):
    # redirect to role-specific dashboard
    if request.user.groups.filter(name='Employer').exists():
        jobs = Job.objects.filter(posted_by=request.user)
        return render(request, 'jobs/employer_dashboard.html', {'jobs': jobs})
    else:
        # applicant
        applications = Application.objects.filter(applicant=request.user)
        return render(request, 'jobs/applicant_dashboard.html', {'applications': applications})

@login_required
def post_job(request):
    if not request.user.groups.filter(name='Employer').exists():
        return redirect('job_list')
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.save()
            return redirect('dashboard')
    else:
        form = JobForm()
    return render(request, 'jobs/post_job.html', {'form': form})

def job_list(request):
    q = request.GET.get('q', '')
    jobs = Job.objects.all().order_by('-created_at')
    if q:
        jobs = jobs.filter(
            Q(title__icontains=q) |
            Q(company_name__icontains=q) |
            Q(location__icontains=q)
        )
    return render(request, 'jobs/job_list.html', {'jobs': jobs, 'q': q})

def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)

    # Check if user is an applicant
    is_applicant = False
    if request.user.is_authenticated:
        is_applicant = request.user.groups.filter(name='Applicant').exists()

    # Optional: get applicants only if employer
    applicants = None
    if request.user.groups.filter(name='Employer').exists():
        applicants = Application.objects.filter(job=job)

    return render(request, "jobs/job_detail.html", {
        "job": job,
        "is_applicant": is_applicant,
        "applicants": applicants,
    })


@login_required
def apply_job(request, pk):
    if request.user.groups.filter(name='Applicant').exists():
        job = get_object_or_404(Job, pk=pk)
        # Prevent duplicate applications (optional)
        if Application.objects.filter(job=job, applicant=request.user).exists():
            return render(request, 'jobs/apply_job.html', {'error': 'You have already applied to this job.'})
        if request.method == 'POST':
            form = ApplicationForm(request.POST, request.FILES)
            if form.is_valid():
                application = form.save(commit=False)
                application.job = job
                application.applicant = request.user
                application.save()
                return redirect('dashboard')
        else:
            form = ApplicationForm()
        return render(request, 'jobs/apply_job.html', {'form': form, 'job': job})
    else:
        return redirect('job_list')
