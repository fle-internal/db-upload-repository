from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class Project(models.Model):
    project_code = models.CharField(
        _("project code"), max_length=120, unique=True)

    def __str__(self):
        return self.project_code


class MyUserManager(BaseUserManager):
    def create_user(self, email, project_code, password=None):
        """
        Creates and saves a User with the given email, password, and project.
        """
        if not email:
            raise ValueError("Users must have an email address")

        if project_code:

            project = Project.objects.get_or_create(project_code=project_code)

        else:

            project = None

        user = self.model(
            email=self.normalize_email(email),
            project=project,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            None,
            password=password,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"

    objects = MyUserManager()

    email = models.EmailField(
        verbose_name=_("email address"),
        max_length=255,
        unique=True,
    )

    full_name = models.CharField(_("full name"), max_length=120, blank=True)
    project = models.ForeignKey(Project, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.email

    def __str__(self):  # __unicode__ on Python 2
        return self.full_name

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin

    @property
    def is_superuser(self):
        return self.is_admin


class FacilitySummary(models.Model):
    project = models.ForeignKey(Project)
    facility_name = models.CharField(_("Facility name"), max_length=100)
    facility_id = models.UUIDField(_("Facility id"))
    generated = models.DateTimeField(_("Summary generated"), auto_now_add=True)
    last_sync = models.DateTimeField(_("Last sync date"))
    num_content_sessions = models.IntegerField(_("Number of content sessions"))
    time_content_sessions = models.FloatField(
        _("Time spent on content sessions"))
    next_summary = models.ForeignKey("self", null=True, blank=True)
