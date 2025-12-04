from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .serializers import (
    UserRegistrationSerializer, 
    LoginSerializer, 
    UserSerializer, 
    UserProfileSerializer
)
from .models import UserProfile, EmailVerification

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        # Create user but mark as inactive until email is verified
        user = serializer.save()
        user.is_active = False
        user.save()
        
        # Create email verification token
        verification = EmailVerification.objects.create(user=user)
        verification.send_verification_email()
        
        return Response({
            'message': 'Registration successful! Please check your email for verification instructions.',
            'email': user.email,
            'verification_required': True
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Check if user's email is verified
        if not user.is_active:
            return Response({
                'error': 'Email not verified. Please check your email for verification instructions.',
                'email_not_verified': True,
                'email': user.email
            }, status=status.HTTP_403_FORBIDDEN)
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    profile = user.profile
    
    # Update user fields
    user_data = {}
    for field in ['first_name', 'last_name', 'email']:
        if field in request.data:
            user_data[field] = request.data[field]
    
    if user_data:
        user_serializer = UserSerializer(user, data=user_data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
        else:
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Update profile fields
    profile_serializer = UserProfileSerializer(profile, data=request.data, partial=True)
    if profile_serializer.is_valid():
        profile_serializer.save()
        return Response(UserSerializer(user).data)
    
    return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    token = request.data.get('token')
    if not token:
        return Response({'error': 'Verification token is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        verification = EmailVerification.objects.get(token=token)
        
        if not verification.is_valid():
            return Response({
                'error': 'Verification token is expired or already used'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Activate user and mark verification as used
        user = verification.user
        user.is_active = True
        user.save()
        
        # Update profile email verification status
        user.profile.email_verified = True
        user.profile.save()
        
        verification.is_used = True
        verification.save()
        
        # Generate tokens for immediate login
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Email verified successfully! You are now logged in.',
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)
        
    except EmailVerification.DoesNotExist:
        return Response({
            'error': 'Invalid verification token'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(email=email)
        
        if user.is_active:
            return Response({
                'error': 'Email is already verified'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Invalidate any existing verification tokens
        EmailVerification.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Create new verification token
        verification = EmailVerification.objects.create(user=user)
        verification.send_verification_email()
        
        return Response({
            'message': 'Verification email sent successfully!'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'error': 'No account found with this email address'
        }, status=status.HTTP_400_BAD_REQUEST)
