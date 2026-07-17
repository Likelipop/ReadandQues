from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q


class UsernameOrEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        try:
            # Check if input matches username or email (case-insensitive)
            user = User.objects.get(Q(username__iexact=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            # Run the password hasher to prevent timing attacks
            User().set_password(password)
        except User.MultipleObjectsReturned:
            # If multiple users match, get the first active one or the first one created
            user = User.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)).order_by('id').first()
            if user and user.check_password(password):
                return user
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
