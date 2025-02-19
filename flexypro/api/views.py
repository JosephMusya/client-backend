from base64 import urlsafe_b64encode
from email import utils
from urllib.parse import parse_qs, urlparse
from django.http import Http404
from django.shortcuts import redirect
import pyotp
from rest_framework import viewsets
from .models import (
    Order, 
    Client, 
    Notification, 
    Solved, 
    Chat,
    Subscribers, 
    User, 
    Transaction, 
    Solution,
    Profile,
    Freelancer, 
    OTP,
    Bid,  
    Rating, 
    SupportChat
    )
from .serializers import (
    EmailSubscribersSerializer,
    OrderSerializer, 
    NotificationSerializer,
    ProfileViewRequestSerializer, 
    SolvedSerializer,
    ChatSerializer,
    SupportChatSerializer,
    TransactionSerializer, 
    SolutionSerializer,
    ProfileSerializer,
    ObtainTokenSerializerClient,    
    ObtainTokenSerializerFreelancer,    
    RegisterSerializer,
    ResetPasswordSerializer,
    setNewPasswordSerializer,
    OTPSerializer,
    BidSerializer,
    FreelancerSettingsSerializer,
    ClientSettingsSerializer,   
)

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from .utils import Util
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_str, force_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from .pagination import OrdersPagination, NotificationsPagination, TransactionsPagination, ChatsPagination, SolutionPagination, BiddersPagination
from . import utils
from drf_yasg.utils import swagger_auto_schema
import stripe
from django.db import transaction

# from django_otp.exceptions import OTPVerificationError

# Create your views here.

class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    
    @swagger_auto_schema(tags=['Password Reset'])
    def post(self, request):
        data={
            'request':request,
            'data': request.data
        }
        serializer = self.serializer_class(data=data)

        email = request.data['email']
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            uidb64 = urlsafe_b64encode(bytes(str(user.id), 'utf-8')).decode('utf-8')
            # uidb64 = user.id

            token = PasswordResetTokenGenerator().make_token(user)
            current_site = get_current_site(request).domain
            relative_link = reverse(
                'password-reset-confirm', kwargs={
                    'uidb64':uidb64,
                    'token':token
                }
            )
            abs_url = f'http://{current_site+relative_link}'

            email_body = f"""
                <html>
                <body style="max-width: 768px; margin: 0 auto; background-color: #fff; border-radius: 10px; font-family: sans-serif; justify-content: flex-start; color: #fff; line-height: 1.8;">
                    <div class="email" style="background-color: #374151; height: fit-content; width: 100%;">
                    <h1 class="top" style="background-color: #404c5e; padding: 2rem; margin: 0;">Password Reset Email</h1>
                    <section style="padding: 2rem; word-wrap: break-word;">
                        <h1>Hi {user.username},</h1>
                        <article>
                        You are receiving this email because you requested a password reset for your <a href="https://clients.gigitise.com" style="text-decoration: none; color: #15c;">Gigitse platform</a> account.
                        </article>
                        <br />
                        <article>Use the link below to reset your password,</article>
                        <article>
                        <a href={abs_url} style="text-decoration: none; color: #15c;">{abs_url}</a>
                        </article>
                        <br />
                        <article>
                        If you did not request password reset for your account, kindly disregard this email. We recommend you review your activity on <a href="https://clients.gigitise.com" style="text-decoration: none; color: #15c;">Gigitse platform</a> to ensure security.
                        </article>
                    </section>
                    <footer style="padding: 1rem 2rem; background-color: #404c5e;">
                        <article>Warm Regards,</article>
                        <article>Gigitise Team.</article>
                    </footer>
                    </div>
                </body>
                </html>
            """
            data = {
                'email_body':email_body,
                'email_subject':'Password Reset',
                'email_to': user.email
            }

            Util.send_email(data=data)
        
            return Response({
                    f'success':'Password reset send to {email}',
                }, status=status.HTTP_200_OK
            )
        return Response({
            'error':'No user with the provided email found'
        }, status=status.HTTP_404_NOT_FOUND)

class PasswordTokenCheckView(generics.GenericAPIView):
    
    swagger_schema = None    
    def get(self, request, uidb64, token):
        try:
            
            id = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=id)

            if not PasswordResetTokenGenerator().check_token(user, token):
                return redirect(f'{settings.USED_TOKEN_URL}{uidb64}/{token}')
            
            return redirect(f'{settings.PASSWORD_RESET_URL}{uidb64}/{token}')                        
        except DjangoUnicodeDecodeError as error:
            return redirect(f'{settings.BAD_TOKEN_URL}{uidb64}/{token}')

class SetNewPasswordView(generics.GenericAPIView):
    serializer_class = setNewPasswordSerializer
        
    swagger_schema = None
    def put(self, request):
        serializer = self.serializer_class(data=request.data)

        serializer.is_valid(raise_exception=True)

        return Response({
            'success':True,
            'message':'Password reset successful'
        }, status=status.HTTP_200_OK)

class TokenPairViewClient(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = ObtainTokenSerializerClient

    @swagger_auto_schema(tags=['Auth'])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
class TokenPairViewFreelancer(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = ObtainTokenSerializerFreelancer

    @swagger_auto_schema(tags=['Auth'])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    # permission_classes = (AllowAny)
    serializer_class = RegisterSerializer

    @swagger_auto_schema(tags=['Auth'])
    def post(self, request):
        # user = request.data
        # print(user)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        user_data = serializer.data
        user = User.objects.get(email=user_data['email'])

        topt = pyotp.TOTP(settings.OTP_KEY)

        otp = Util.generate_otp(topt)

        OTP.objects.create(
            otp = otp,
            user = user
        )

        # user.save()

        # token = RefreshToken.for_user(user).access_token

        # current_site = get_current_site(request).domain
        # relative_link = reverse('verify-email')
        # abs_url = f'http://{current_site+relative_link+"?token="+str(token)}'
        # email_body = f'Hi {user.username} \nYour OTP is {otp}'
        email_body = f"""
            <html>
                <html>
                <body style="max-width: 600px; margin: 0 auto; background-color: #fff; border-radius: 10px; font-family: sans-serif; color: #fff; line-height: 1.8;">
                    <div class="email" style="background-color: #374151; height: fit-content;">
                    <div class="top" style="background-color: #404c5e; padding: 2rem;">
                        <h1 style="margin: 0;">Gigitise Email Verification</h1>
                    </div>
                    <section style="padding: 2rem; color: #fff; word-wrap: break-word;">
                        <h1 style="margin: 0; color: #fff;">Hi {user.username},</h1>
                        <article style="color: #fff;" class="intro-p">
                        Welcome to Gigitise! We are thrilled to have you onboard our platform and excited for the journey ahead. As you embark on this digital adventure with us, we want to ensure a seamless and secure experience every step of the way.
                        </article>
                        <h1 class="otp" style="display: flex; align-items: center; gap: 1rem;"><strong style="font-size: 32px; color: #fff;;">Your OTP is {otp}</strong></h1>
                        <article>
                        This OTP will be valid for a single use and ensures that your account remains protected. Please keep it confidential and do not share it with anyone.
                        </article>
                    </section>
                    <footer style="padding: 1rem 2rem; background-color: #404c5e;">
                        <div>
                        Best regards,<br />
                        Gigitise Team.
                        </div>
                    </footer>
                    </div>
                </body>
            </html>
            """
        data = {
            'email_body':email_body,
            'email_subject':'Email Verification',
            'email_to': user.email
        }

        Util.send_email(data=data)

        return Response(user_data, status=status.HTTP_201_CREATED)
    
class CreateCheckoutOrderView(generics.GenericAPIView):
    @swagger_auto_schema(tags=['Paypal payment'])
    def post(self, request):  
        try:   
            order_id = request.data['orderId']
            order = Order.objects.get(id=order_id)        
            amount = order.amount
            access_token = utils.get_token()

            # Create order
            order = utils.create_order(amount=amount, access_token=access_token)
            id = order['id']
            return Response({
                'id':id
            }, status=status.HTTP_200_OK)
        except:
            return Response({
                'error':'Error while creating payment'
            }, status=status.HTTP_400_BAD_REQUEST)

class CapturePaymentView(generics.GenericAPIView):

    @swagger_auto_schema(tags=['Paypal payment'])
    def post(self, request):
        try:
            paypalId = request.data['paypalId']
            orderId = request.data['orderId']
            order = Order.objects.get(id=orderId)
            access_token = utils.get_token()
            paypal_id, amount_value, paypal_fee_value, net_amount_value, currency_code, status_value = utils.capture_payment(paypalId, access_token)

            # Modify order to paid true, and create transaction table data
            if not order.paid:
                order.paid = True
                order.save()
                Transaction.objects.create(
                    transaction_id = paypal_id,
                    order = order,
                    status = status_value,
                    amount_value = amount_value,
                    paypal_fee_value = paypal_fee_value,
                    net_amount_value = net_amount_value,
                    currency_code = currency_code,
                    channel = 'Paypal',  
                    _from  = order.client.user,
                    _to = order.freelancer.user       
                )

            return Response({
                'success':'Purchase complete'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(e)
            return Response({
                'error':'Error occured during transaction'
            }, status=status.HTTP_400_BAD_REQUEST)

class StripeCheckoutView(generics.GenericAPIView):
    def post(self, request):
        stripe.api_key = settings.STRIPE_API_KEY
        order_id = request.data.get('order_id',)
        order = Order.objects.filter(id=order_id)
        try:
            amount = self.convert_to_cents(order.first().amount)
            quantity = order.count()
            try:
                checkout_session = stripe.checkout.Session.create(
                    ui_mode = 'embedded',
                    line_items = [
                        {
                            'price_data':{
                                'currency':'usd',
                                'unit_amount':amount,
                                'product_data':{
                                    'name':str(order_id)
                                }                                
                            },
                            'quantity':quantity
                        }
                    ],
                    
                    mode = 'payment',
                    return_url = settings.REDIRECT_DOMAIN + f'/payment/?session_id={{CHECKOUT_SESSION_ID}}&order_id={order_id}',
                    # success_url = settings.REDIRECT_DOMAIN + '/payment_success/?session_id={CHECKOUT_SESSION_ID}',
                    # cancel_url = settings.REDIRECT_DOMAIN + '/payment_cancelled',
                )
                
                return Response({
                    'client_secret':checkout_session.client_secret
                }, status=status.HTTP_200_OK)
            except  Exception as e:
                print(e)
                return Response({
                    'error':str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            raise NotFound('We could not find the order')
        except Exception as e:
            print(e)
            return Response({
                'error': str(e)
            })
            
    def convert_to_cents(self, amount):
        return int(amount*100)

class CaptureStripeStatusView(generics.GenericAPIView):
    def get(self, request):
        session_id = self.request.GET.get('session_id')
        order_id = self.request.GET.get('order_id')
        stripe.api_key = settings.STRIPE_API_KEY
        session = stripe.checkout.Session.retrieve(session_id)
        if session.status == "complete":
            pass
            # save to db
            # Transaction.objects.create(
                
            # )

        return Response({
            'status': session.status,
            'email':session.customer_details.email,
            'session_id':session_id,
            'amount':session.amount_total/100,
            'time':session.created,           
        })

class StripeWebHookView(generics.GenericAPIView):
    def post(self, request):
        stripe.api_key = settings.STRIPE_API_KEY
        payload = request.body
        signature_header = self.request.META['HTTP_STRIPE_SIGNATURE']
        event = None
        try:
            event = stripe.Webhook.construct_event(
                payload, signature_header, settings.STRIPE_CHECKOUT_WEBHOOK
            )
        except Exception as e:
            print(e)
            return Response({
                'error':'Failed to create webhook'
            }, status=status.HTTP_400_BAD_REQUEST)     
            
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            amount = session.get('amount_total', None)
            transaction_id = session.get('id', None)
            return_url = urlparse(session.get('return_url'))
            query_params = parse_qs(return_url.query)
            print(query_params)
            order_id = query_params.get('order_id', [None])[0]
            currency = session.get('currency','')
            status = session.get('status','')

            order = Order.objects.get(id=order_id)
            if not order.paid:
                order.paid = True
                order.save()
                try:
                    Transaction.objects.create(
                        transaction_id = transaction_id,
                        order = order,
                        _from = order.client.user,
                        _to = order.freelancer.user,
                        amount_value = self.convert_to_unit(amount),
                        net_amount_value = self.convert_to_unit(amount),
                        currency_code = currency.upper(),
                        channel = 'Stripe',
                        status = status.upper(),               
                    )
                except Exception as e:
                    print(e)
                    
        return Response({
                'details':'Transaction completed'
            })  
    def convert_to_unit(self, amt):
        return amt/100

class ResendOTPView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(tags=['Resend OTP'])
    def get(self, request):
        try:            

            user = User.objects.get(username=self.request.user)

            if not user.is_verified:
                topt = pyotp.TOTP(settings.OTP_KEY)

                otp = Util.generate_otp(topt)

                OTP.objects.create(
                    otp = otp,
                    user = user
                )

                # email_body = f'Hi {user.username} \nYour OTP is {otp}'
                email_body = f"""
                    <html>
                        <html>
                        <body style="max-width: 600px; margin: 0 auto; background-color: #fff; border-radius: 10px; font-family: sans-serif; color: #fff; line-height: 1.8;">
                            <div class="email" style="background-color: #374151; height: fit-content;">
                            <div class="top" style="background-color: #404c5e; padding: 2rem;">
                                <h1 style="margin: 0;">Gigitise Email Verification</h1>
                            </div>
                            <section style="padding: 2rem; color: #fff; word-wrap: break-word;">
                                <h1 style="margin: 0; color: #fff;">Hi {user.username}</h1>
                                <article style="color: #fff;" class="intro-p">
                                Welcome to Gigitise! We are thrilled to have you onboard our platform and excited for the journey ahead. As you embark on this digital adventure with us, we want to ensure a seamless and secure experience every step of the way.
                                </article>
                                <h1 class="otp" style="display: flex; align-items: center; gap: 1rem;"><strong style="font-size: 46px; color: #fff;;">Your OTP is {otp}</strong></h1>
                                <article>
                                This OTP will be valid for a single use and ensures that your account remains protected. Please keep it confidential and do not share it with anyone.
                                </article>
                            </section>
                            <footer style="padding: 1rem 2rem; background-color: #404c5e;">
                                <div>
                                Best regards,<br />
                                Gigitise Team.
                                </div>
                            </footer>
                            </div>
                        </body>
                    </html>
                    """

                data = {
                    'email_body':email_body,
                    'email_subject':'Email Verification',
                    'email_to': user.email
                }

                Util.send_email(data=data)

                return Response({
                    'success':'OTP resend successfully'
                },status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'detail':'User already verified'
                },status=status.HTTP_400_BAD_REQUEST)
        
        except Exception:
            return Response({
                'error': 'Invalid request'
            }, status=status.HTTP_400_BAD_REQUEST)

class VerifyUserAccountView(generics.GenericAPIView):
    serializer_class = OTPSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(tags=['Auth'])
    def post(self,request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data['otp']
        user = User.objects.get(username=self.request.user)
        otp_object = OTP.objects.filter(user=user).last()

        # print(f'Token found {token}')                
            # payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            # user = User.objects.get(id=payload['user_id'])
        try:
            if not user.is_verified:
                valid = Util.verify_otp(self, otp, otp_object)
                
                if valid:
                    if not user.is_verified:
                        user.is_verified = True
                        otp_object.used = True
                        otp_object.save()
                        try:
                            user.save()
                        except Exception as e:
                            print(e)
                        return Response({
                            'success':'Account activation success'
                        }, status=status.HTTP_200_OK)
                elif otp != otp_object.otp:
                    return Response({
                        'error':'Invalid OTP'
                    }, status=status.HTTP_400_BAD_REQUEST)
                elif otp_object.used:
                    return Response({
                        'error':'OTP already used'
                    }, status.HTTP_400_BAD_REQUEST)                       
            else:
                return Response({
                'error':'User already verified'
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception:
            return Response({
                    'error':'No OTPs found'
                }, status.HTTP_400_BAD_REQUEST) 
        # except jwt.ExpiredSignatureError as error:            
            # return redirect(f'{settings.APP_HOME}/request-newtoken')
            # return Response({
            #     'error':'Activation link expired'
            # }, status=status.HTTP_400_BAD_REQUEST)        
        
        # except jwt.exceptions.DecodeError as error:
        #     # return redirect(f'{settings.APP_HOME}/request-newtoken')
        #     return Response({
        #         'error':'Invalid Token',
        #     }, status=status.HTTP_400_BAD_REQUEST)

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'update', 'put', 'delete']    
    pagination_class = OrdersPagination
    
    @swagger_auto_schema(tags=['Order'])
    def list(self, request, *args, **kwargs):
        # self.serializer_class = OrderListSerializer
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Order'])
    def create(self, request, *args, **kwargs):        
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():   
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            print(serializer.errors)
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(tags=['Order'])
    def perform_create(self, serializer):
        user = self.request.user
        client = Client.objects.get(user = user)
        unique_code = Util.generate_order_code(length=8)
                    
        serializer.save(client=client, unique_code=unique_code )

    def get_queryset(self):
        user = self.request.user
        status = self.request.GET.get('status', None)
        bidding = self.request.GET.get('bidding', None)        
        query = Q(client__user=user) | Q(freelancer__user=user)          

        if status or bidding:
            if status == 'available':
                try:
                    if Client.objects.filter(user=user).exists():
                        return Order.objects.filter(client__user=user, status='Available').order_by('-updated')
                    elif Freelancer.objects.filter(user=user).exists():
                        return Order.objects.filter(status='Available').order_by('-updated').exclude(bid_set__freelancer__user=user)
                except:
                    raise NotFound('No available orders')
                
            elif status == 'in_progress':    
                try:            
                    return Order.objects.filter(query, Q(status='In Progress')).order_by('-updated')
                except:
                    raise NotFound('No orders in progress')
                
            elif status == 'completed':
                try:
                    return Order.objects.filter(query, Q(status='Completed')).order_by('-updated')
                except:
                    raise NotFound('No completed orders found')
                
            elif bidding =='true':
                try:
                    Freelancer.objects.get(user=user)
                    return Order.objects.filter(bid_set__freelancer__user=user)
                except:
                    raise NotFound('No orders in bidding stage')
                    
            else:
                # Handle invalid status parameter
                raise Http404("Invalid status parameter")

        return Order.objects.filter(query).order_by('-updated')
            
    @swagger_auto_schema(tags=['Order'])
    def retrieve(self, request, *args, **kwargs):
        order_id = self.kwargs.get('pk')  # Assuming 'pk' is used for order ID in the URL
        try:
            order = Order.objects.get(id=order_id)    
            serializer = self.get_serializer(order)            
            return Response(serializer.data)
        except Order.DoesNotExist:
            raise NotFound('Order not found')

    @swagger_auto_schema(tags=['Order'])
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=['Order'])
    def destroy(self, request, *args, **kwargs):    
        order_id = self.kwargs.get('pk')

        try:
            order = self.get_object()

            if order.client.user != self.request.user:
                return Response({
                    'error':'Action not allowed'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if order.status != 'Available':
                return Response({
                    'error':'You can only delete orders available'
                }, status=status.HTTP_400_BAD_REQUEST)
              
            self.perform_destroy(order)
            return Response({'success':order_id})
        
        except Order.DoesNotExist:
            raise NotFound('Order not found')
        
    def get_object(self):
        order_id = self.kwargs.get('pk')
        queryset = self.filter_queryset(self.get_queryset())

        try:
            obj = queryset.get(id=order_id)
            return obj
        except:
            raise NotFound("The order was not found")

    @swagger_auto_schema(tags=['Order'])
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True

        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=['Bid'])
    @action(detail=True, methods=['post'], url_path='bid')
    def place_bid(self, request, pk=None):
        order_id =self.kwargs.get('pk')
        order = Order.objects.filter(id=order_id, status='Available').first()
        client = order.client
        # user = User.objects.get(username=request.user)
        user = request.user
        freelancer = Freelancer.objects.get(user=user)        

        try:            
            bid_amount = float(request.data['amount'])
            if bid_amount < order.amount:
                return Response({
                    'error':'Bid amount should be higher than order amount'
                }, status=status.HTTP_400_BAD_REQUEST)
            Bid.objects.create(
                order = order,
                freelancer = freelancer,
                client = client,
                amount = bid_amount
            )
            
            updated_order = Order.objects.filter(id=order_id,).first()

            serializer = OrderSerializer(updated_order)
            return Response(serializer.data)            
        except Exception as e:
            print(e)
            return Response({
                'error':'Error placing bid'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(tags=['Bid'])
    @place_bid.mapping.put
    def update_bid(self, request, pk=None):
        order_id =self.kwargs.get('pk')
        order = Order.objects.filter(id=order_id, status='Available').first()
        user = request.user
        freelancer = Freelancer.objects.get(user=user) 

        try:            
            amt = float(request.data['amount'])

            if amt < order.amount:
                return Response({
                    'error':'Bid amount should be higher than order amount'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            q = Q(freelancer=freelancer) | Q(order=order)

            try:
                bid = Bid.objects.filter(q).first()
                bid.amount = amt
                bid.save() 
                _bid = Bid.objects.filter(q).first()
                serializer = BidSerializer(bid)

                return Response(serializer.data)
            
            except Bid.DoesNotExist:
                raise NotFound('Bid does not exist')
                  
        except Exception as e:
            print(e)
            return Response({
                'error':'Error updating bid'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(tags=['Bid'])
    @place_bid.mapping.delete
    def cancel_delete(self, request, pk=None):
        order_id =self.kwargs.get('pk')
        order = Order.objects.filter(id=order_id, status='Available').first()
        user = request.user
        freelancer = Freelancer.objects.get(user=user) 

        try:      
            # q = Q(freelancer=freelancer) | Q(order=order)
            try:
                bid = Bid.objects.filter(freelancer=freelancer, order=order).first()
                bid.delete()
                updated_order = Order.objects.filter(id=order_id,).first()

                serializer = OrderSerializer(updated_order)
                return Response(serializer.data)    
            except:
                raise NotFound('Bid not found')        
                    
        except Exception as e:
            print(e)
            return Response({
                'error':'Error deleting bid'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(tags=['Bid'])
    @action(detail=True, methods=['get'], url_path='bidders')
    def get_bidders(self, request, pk=None):
        bidderParams = self.request.GET.get('bidder',None)
        if (bidderParams):
            try:
                bid = Bid.objects.get(id=bidderParams)
                serializer = BidSerializer(bid)
                print(serializer.data)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Bid.DoesNotExist:
                raise NotFound("Bidder not found")
            
            except:
                return Response({"error": "Can't retrieve bidder"},status=status.HTTP_400_BAD_REQUEST)
            
        order = self.get_object()
        bidders = Bid.objects.filter(order=order)
        paginator = BiddersPagination()
        results = paginator.paginate_queryset(bidders, request)
        serializer = BidSerializer(results, many=True)
        
        data = {
            'count': paginator.page.paginator.count,
            'next': paginator.get_next_link(),
            'previous': paginator.get_previous_link(),
            'results': serializer.data
        }
        return Response(data)

    @swagger_auto_schema(tags=['Order Solution'])
    @action(detail=True, methods=['get'], url_path='solution')
    def get_solution(self, request, pk=None):
        order = self.get_object()
        solution = Solution.objects.filter(order=order)
        paginator = SolutionPagination()
        results = paginator.paginate_queryset(solution, request)
        serializer = SolutionSerializer(results, many=True)
        
        data = {
            'count': paginator.page.paginator.count,
            'next': paginator.get_next_link(),
            'previous': paginator.get_previous_link(),
            'results': serializer.data
        }
        return Response(data)
    
    @swagger_auto_schema(tags=['Order Solution'])
    @get_solution.mapping.delete
    def delete_solution(self, request, pk=None):
        solution_id = self.request.GET.get('solution-id')
        order = self.get_object()
        if (order.status == 'Completed'):
            return Response({
                'error':'Not allowed'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            solution = Solution.objects.get(id=solution_id)
            solution.delete()
            return Response({
                'id':solution_id
            }, status=status.HTTP_200_OK)
        except Solution.DoesNotExist:
            raise NotFound('Solution not found')

    
    # @action(detail=True, methods=['post'], url_path='create-solution')
    @swagger_auto_schema(tags=['Order Solution'])
    @get_solution.mapping.post
    def post_solution(self, request, pk=None):
        order = self.get_object()
        parser_classes = (MultiPartParser, FormParser)
        print(request.data)
        serializer = SolutionSerializer(data=request.data, context={'request': request})        
        if serializer.is_valid():
            serializer.save(
                order=order,                
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print(serializer.error_messages)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)    

    @swagger_auto_schema(tags=['Chat'])
    @action(detail=True, methods=['get'], url_path='chats')
    def order_chats(self, request, pk=None):
        order_id =self.kwargs.get('pk')
        try:
            order = Order.objects.filter(id=order_id,).first()
            if order.status != 'Available':
                order = self.get_object()
            chats = Chat.objects.filter(order=order)
            paginator = ChatsPagination()
            results = paginator.paginate_queryset(chats, request)
            serializer = ChatSerializer(results, many=True)
            
            data = {
                'count': paginator.page.paginator.count,
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
                'results': serializer.data
            }
            return Response(data)
        except Order.DoesNotExist:
            raise NotFound("Order not found")
        except Exception as e:
            print(e)
            return Response({
                "error":"Can't retrieve chats"
            }, status = status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(tags=['Chat'])
    @order_chats.mapping.post
    def create_chat(self, request, pk=None):
        try:
            order_id =self.kwargs.get('pk')
            order = Order.objects.filter(id=order_id,).first()
            if order.status != 'Available':
                order = self.get_object()
            sender = request.user
            receiver_username = request.data['receiver']
            receiver = User.objects.get(username=receiver_username)

            serializer = ChatSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(
                    order=order,
                    sender = sender,
                    receiver = receiver
                )    
                
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response({
                'error':'Failed to create chat'
            }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(['Rating'])
    @action(detail=True, methods=['post'], url_path='rating')
    def addRating(self, request, pk=None):
        try:
            order_id = self.kwargs.get('pk')
            order = Order.objects.filter(id=order_id,).first()
            data = self.request.data
            stars = data.get('stars')
            message = data.get('message')
            
            try:
                Rating.objects.create(
                message=message,
                stars = stars,
                order = order
                )  
                
            except:
                return Response({
                    'error': 'Error adding rating'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            order = Order.objects.filter(id=order_id,).first()
            serialized_data = OrderSerializer(order)
            return Response(serialized_data.data)
            
        except Order.DoesNotExist:
            raise NotFound('Order not found')
        except Exception as e:
            print(e)
            return Response({
                'error':'Error occured'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        
    
class BidView(generics.GenericAPIView):
    serializer_class = BidSerializer()

    def get(self):
        user = self.request.user
        freelancer = Freelancer.objects.get(user=user)
        user_bids = Bid.objects.filter(freelancer=freelancer)
        return Response(self.get_serializer(user_bids))


class HireWriterView(generics.GenericAPIView):
    
    @swagger_auto_schema(tags=['Order'])
    def post(self, request):
        try:
            bid_id = request.data['bidId']
            try:
                bid = Bid.objects.get(id=bid_id)
                order = bid.order
                amount = bid.amount
                freelancer = bid.freelancer
                order.amount = amount
                order.freelancer = freelancer
                order.status = 'In Progress'
                order.save()
                                                
                # notify_freelancer(order, freelancer)

                Bid.objects.filter(order=order).delete()
            except:
                raise NotFound("Bid not found")

            return Response({
                'success':'Order allocated to freelancer'
            })
        except:
            return Response({
                'error':'Error hiring writer'
            }, status=status.HTTP_400_BAD_REQUEST)

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get','put']

    @swagger_auto_schema(tags=['Profile'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=['Profile'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Profile'])
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        instance = self.get_object()

        if request.data.get('settings', {}):
            user = instance.user
            try:
                if Freelancer.objects.filter(user=user).exists():
                    freelancer_instance = Freelancer.objects.get(user=user)
                    freelancer_serializer = FreelancerSettingsSerializer(
                        freelancer_instance, data=request.data.get('settings', {}), partial=True
                    )
                    freelancer_serializer.is_valid(raise_exception=True)
                    freelancer_serializer.save()
                elif Client.objects.filter(user=user).exists():
                    client_instance = Client.objects.get(user=user)
                    client_serializer = ClientSettingsSerializer(
                        client_instance, data=request.data.get('settings', {}), partial=True
                    ) 
                    client_serializer.is_valid(raise_exception=True)
                    client_serializer.save()
                    
            except User.DoesNotExist:
                raise NotFound("User not found!")

        return super().update(request, *args, **kwargs)
    
    def get_serializer_class(self):
        user_params = self.request.GET.get('user')
        

        if user_params:
            return ProfileViewRequestSerializer
        else:
            return ProfileSerializer
        
    
    def get_queryset(self):
        current_user = self.request.user
        user_params = self.request.GET.get('user')
                
        if user_params:            
            try: 
                user = User.objects.get(username=user_params)                                              
                return self.queryset.filter(user=user)          
            except user.DoesNotExist:
                raise NotFound("Profile not found")
                
        else:
            return self.queryset.filter(user=current_user)
    
    

# class BidViewSet(viewsets.ModelViewSet):
#     permission_classes = [IsAuthenticated]
#     serializer_class = BidSerializer
#     queryset = Bid.objects.all()

#     def create(self, request, *args, **kwargs):
#         freelancer = self.request.user
#         serializer = self.serializer_class(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         order_id = serializer.validated_data['orderId']
#         order = Order.objects.get(id=order_id)
#         order.freelancer = freelancer

#     def update(self, request, *args, **kwargs):
#         kwargs['partial'] = True
#         return super().update(request, *args, **kwargs)
    
#     def get_queryset(self):
#         user = self.request.user
#         query = Q(client__user=user) | Q(freelancer__user=user)
#         return self.queryset.filter(query).order_by('-created_at')

class NotificationViewSet(viewsets.ModelViewSet):    
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get','put']
    pagination_class = NotificationsPagination
    
    @swagger_auto_schema(tags=['Notification'])
    def list(self, request, *args, **kwargs):
        self.request.GET.get('status', None)
        params = self.request.GET.get('status')
        
        if params == 'unread_count':
            unread_count = self.get_unread_count(request.user)
            return Response({
                'unread_count': unread_count
            })
        
        user = request.user
        unread_count = Notification.objects.filter(user=user, read_status=False).count()
        response = super().list(request, *args, **kwargs)
        response.data['unread_count'] = unread_count
        return response

    @swagger_auto_schema(tags=['Notification'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Notification'])
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)


    @swagger_auto_schema(tags=['Notification'])
    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Notification'])
    def get_queryset(self):
        user = self.request.user        
        return self.queryset.filter(user=user).order_by('-created_at')

    def get_unread_count(self, user):
        return Notification.objects.filter(user=user, read_status=False).count()
    
class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']
    pagination_class = TransactionsPagination

    @swagger_auto_schema(tags=['Transactions'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=['Transactions'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:    
            return self.queryset.filter(_to=user)  

        q = Q(_from = user) | Q(_to = user)
        return self.queryset.filter(q).order_by('-timestamp')


class SubscribeToEmailView(generics.GenericAPIView):
    
    serializer_class = EmailSubscribersSerializer
    
    @swagger_auto_schema(tags=['Subscribe'])
    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            
            return Response({
                    'success':'Subscription success'
                })
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
    @swagger_auto_schema(tags=['Subscribe'])
    def get(self, request):
        
        try:
            subs = Subscribers.objects.all()

            serializer = self.serializer_class(subs, many=True)
            return Response(serializer.data)
        except:
            return Response({"error":"Error retrieving email lists"})


class SupportChatViewSet(viewsets.ModelViewSet):
    queryset = SupportChat.objects.all()
    serializer_class = SupportChatSerializer
    http_method_names = ['get', 'post',]    
    permission_classes = [IsAuthenticated]
    pagination_class = ChatsPagination
    
    @swagger_auto_schema(tags=['Support'])
    def list(self, request, *args, **kwargs):
        paginator = SolutionPagination()
        user = self.request.user
        
        # return Response(data)
        try:
            # order = self.request.query_params.get('order', None)
            chats = self.queryset.filter()
            results = paginator.paginate_queryset(chats, request)
            serializer = SupportChatSerializer(results, many=True)
            
            
            chats = self.queryset.filter(Q(sender=user)|Q(receiver=user))
            
            results = paginator.paginate_queryset(chats, request)
            serializer = self.get_serializer(results, many=True) 
            data = {
                'count': paginator.page.paginator.count,
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
                'results': serializer.data
            }               
            return Response(data)

        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(tags=['Support'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Support'])
    def create(self, request, *args, **kwargs):        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():   
            # self.perform_create(serializer)
            receiver_username = self.request.data['receiver']
        
            user = self.request.user
            message = self.request.data['message']
            topic = self.request.data['topic']
            receiver = User.objects.get(username=receiver_username)  
            order = self.request.query_params.get('order', None)
            
            if Order.objects.filter(id=order).exists():
                order = Order.objects.get(id=order)
                created_message = SupportChat.objects.create(
                    message = message,
                    topic=topic,
                    receiver = receiver,
                    order=order,
                    sender=user
                )
                
                serialized_message = SupportChatSerializer(created_message)
                # print(serialized_message) 
                return Response(serialized_message.data)                       
                
                # return Response(serialized_message.data, status=status.HTTP_201_CREATED)
            else:    
                created_message = SupportChat.objects.create(
                    message = message,
                    topic=topic,
                    receiver = receiver,
                    sender=user
                )
                
                serialized_message = SupportChatSerializer(created_message).data

                # Return the serialized data in the HTTP response
                return Response(serialized_message, status=status.HTTP_201_CREATED) 
                # headers = self.get_success_headers(serializer.data)
                # return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            print(serializer.errors)
            return Response(serializer.data, status=status.HTTP_400_BAD_REQUEST)
        
'''--------------------------To be implemented fully--------------------------------'''

class SolvedViewSet(viewsets.ModelViewSet):
    queryset = Solved.objects.all()
    serializer_class = SolvedSerializer

    swagger_schema = None        

    def get_object(self):
        order_id = self.kwargs.get('pk')
        queryset = self.filter_queryset(self.get_queryset())

        try:
            obj = queryset.get(id=order_id)
            self.check_object_permissions(self.request, obj)
            return obj
        except:
            raise NotFound("The order was not Found")

def new_order_created(order_instance, client,):    
    serialized_data = OrderSerializer(order_instance).data
    response_data = {
        "order":serialized_data
    }

    channel_layer = get_channel_layer()
    client_room_id = client.id
    freelancer_room_id = 'freelancer'
    
    async def send_order():

        freelancer_room = f'order_{freelancer_room_id}' 
        client_room = f'order_{client_room_id}'  

        try:
            # Sending order to freelancer
            await channel_layer.group_send(
                freelancer_room, {
                    'type':'new.order',
                    'message':response_data
                }
            )

            # Sending order to client (owner)
            await channel_layer.group_send(
                client_room, {
                    'type':'new.order',
                    'message':response_data
                }
            )
        except Exception as e:
            print("Error => ", e)


    async_to_sync(send_order)()
    return Response(response_data) 

def send_message_signal(receiver, sender, instance):

    serialized_data = ChatSerializer(instance).data
    serialized_data['order'] = str(serialized_data['order'])
    response_data = {
        'sent_message':serialized_data
    }

    channel_layer = get_channel_layer()

    room_name = f'chat_{receiver.id}'

    async def send_message():
        try:
            await channel_layer.group_send(
                room_name, {
                    'type': 'new.chat',
                    'message': response_data
                }
            )
        except Exception as e:
            print("Error => ", e)

    async_to_sync(send_message)()
    return Response(response_data) 

def new_support_message(receiver, instance):
    serialized_data = SupportChatSerializer(instance).data
    serialized_data['order'] = str(serialized_data['order'])
    response_data = {
        'sent_message':serialized_data
    }
        
    channel_layer = get_channel_layer()
    
    room_name = f'support_{receiver.id}'
        
    async def send_support_message():
        try:
            await channel_layer.group_send(
                room_name, {
                    'type': 'support.chat',
                    'message': response_data
                }
            )
        except Exception as e:
            print("Error => ", e)

    async_to_sync(send_support_message)()
    return Response(response_data) 
    


def send_alert(instance, user):
    channel_layer = get_channel_layer()
    room_name  =f'notifications_{user.id}'

    serialized_data = NotificationSerializer(instance).data
    response_data = {
        'notification':serialized_data
    }

    async def send_notification():
        try:
            await channel_layer.group_send(
                room_name, {
                    'type':'new.notification',
                    'message':response_data
                }
            )
        except Exception as e:
            print("Error => ", e)
    
    async_to_sync(send_notification)()
    return Response(response_data)

def send_bidding_add(instance, user):
    channel_layer = get_channel_layer()
    room_name = f'bids_{user.id}'
    serialized_data = BidSerializer(instance).data
    # print(serialized_data)
    serialized_data['order'] = str(serialized_data['order'])
    
    response_data = {
        'bid': serialized_data,
        'delete': False,
        
    }
    
    async def send_new_bid():
        try:
            await channel_layer.group_send(
                room_name, {
                    'type':'new.bid',
                    'message':response_data,

                }
            )
        except Exception as e:
            print("Error ", e)
    
    async_to_sync(send_new_bid)()
    return Response(response_data)

def send_bidding_delete(instance, user):
    channel_layer = get_channel_layer()
    room_name = f'bids_{user.id}'
    serialized_data = BidSerializer(instance).data
    serialized_data['order'] = str(serialized_data['order'])
    
    response_data = {
        'bid': serialized_data,
        'delete': True,     
    }
    
    async def send_new_bid():
        try:
            await channel_layer.group_send(
                room_name, {
                    'type':'new.bid',
                    'message':response_data,
                }
            )
        except Exception as e:
            print("Error ", e)
    
    async_to_sync(send_new_bid)()
    return Response(response_data)

def send_alert_order(instance, user):
    channel_layer = get_channel_layer()
    room_name = f'hire_{user.id}'

    # Serialize the instance
    serialized_data = OrderSerializer(instance).data
    
    # Convert UUID objects to strings and replace them in the serialized data
    for i, bidder in enumerate(serialized_data['bidders']):
        serialized_data['bidders'][i]['order'] = str(bidder['order'])
        
    response_data = {'order': serialized_data}
    
    async def send_alert():        
        try:    
            await channel_layer.group_send(
                room_name, {
                    'type': 'hire.order',
                    'message': response_data
                }
            )
        except Exception as e:
            print("Error=> ", e)

    # Call the asynchronous function
    async_to_sync(send_alert)()
    
    return Response(response_data)

def send_alert_solution(instance, user):
    channel_layer = get_channel_layer()
    room_name = f'solutions_{user.id}'
    # serialized_data = SolutionSerializer(instance).data
    # serialized_data['order'] = str(serialized_data['order'])
    response_data = {
        'solution': 'serialized_data',
    }
    
    async def send_new_solution():
        try:
            await channel_layer.group_send(
                room_name, {
                    'type':'new.solutions',
                    'message':'response_data',
                }
            )
        except Exception as e:
            print("Error ", e)
    
    async_to_sync(send_new_solution)()
    return Response(response_data)

def send_alert_completed(instance, user):
    channel_layer = get_channel_layer()
    room_name = f'completed_{user.id}'

    # Serialize the instance
    serialized_data = OrderSerializer(instance).data
    response_data = {'order': serialized_data}
    
    async def send_alert():
        try:    
            await channel_layer.group_send(
                room_name, {
                    'type': 'completed.order',
                    'message': response_data
                }
            )
        except Exception as e:
            print("Error=> ", e)

    # Call the asynchronous function
    async_to_sync(send_alert)()
    
    return Response(response_data)

# def send_alert_support(instance, user):
#     channel_layer = get_channel_layer()
#     room_name = f'support_{user.id}'
    
#     serialized_data = SupportChatSerializer(instance).data
#     response_data = {'chat': serialized_data}
#     async def send_alert():
#         try:    
#             await channel_layer.group_send(
#                 room_name, {
#                     'type': 'support.chat',
#                     'message': response_data
#                 }
#             )
#         except Exception as e:
#             print("Error=> ", e)

#     # Call the asynchronous function
#     async_to_sync(send_alert)()
    
#     return Response(response_data)
