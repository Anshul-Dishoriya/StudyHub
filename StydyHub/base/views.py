from django.shortcuts import render ,HttpResponse  ,redirect
from django.contrib.auth  import authenticate , login , logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages

from django.db.models import Q
from base.models import Room , Topic , Message , UserFollowers , UserFollowing
from base.forms import RoomForm , UserForm

from .utils import get_topics ,get_messages


def registerUser(request):
    form = UserCreationForm()

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request , user)
            return redirect('home')
        else:
            messages.error(request , 'An error occurred durign registration!')
    
    context = {'form':form}
    return render(request, 'base/login_register.html' , context)


def loginUser(request):
    page = 'login'

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')

        try : 
            user = User.objects.get(username=username)
        except:
            messages.error(request, "User does not exist!")

        user = authenticate(request , username=username , password = password)
        if user is not None:
            login(request ,user)
            return redirect('home')
        else :
            messages.error(request, "Username OR Password does not exist")


    context = {'page':page}
    return render(request ,'base/login_register.html' , context)



def logoutUser(request):
    logout(request)
    return redirect('home')

def home(request):
    q = request.GET.get('q')
    print(q)
    if q is None:
        q = ''
    
    rooms = Room.objects.filter(
        Q(topic__name__icontains=q)|
        Q(name__icontains=q)|
        Q(description__icontains=q)
    )
    
    room_counts = rooms.count()
    #to display the recent activity
    room_messages = Message.objects.filter(room__name__icontains=q)[:10]
    context={'rooms':rooms , 'room_counts':room_counts , 'room_messages':room_messages}
    
    # to add topics in context 
    get_topics(request , context)
    return render(request, 'base/home.html' ,context )



def room(request ,pk):# here pk = primary key to identify the room
    room = Room.objects.get(id = pk)
    room_messages = room.message_set.all().order_by('-created') # message_set will give us all children of the room
    participants = room.participants.all()
    if request.method == 'POST':
        message = Message.objects.create(
            user = request.user,
            room = room,
            body = request.POST.get('body')
        )
        room.participants.add(request.user)
        return redirect('room' , pk=room.id)

    context = {'room' : room, 'room_messages':None ,
                'participants':participants}
    get_messages(request , context , room_messages)
    return render(request ,'base/room.html' ,context)

@login_required(login_url='login')
def subscribeTopic(request ,pk):
    topic = Topic.objects.get(id=pk)
    is_subscribed = topic.subscribe.filter(id=request.user.id)
    
    if is_subscribed:
        topic.subscribe.remove(request.user.id)
    else :
        topic.subscribe.add(request.user.id)
    # print(dict(request.META))
    return redirect('home')


def userProfile(request , pk):# here pk = primary key to identify the user
    user = User.objects.get(id=pk)
    rooms = user.room_set.all()
    user_followers = UserFollowers.objects.filter(myFollower=user)
    user_followings = UserFollowing.objects.filter(myFollowing=user)


    is_following = False
    if request.user.is_authenticated and UserFollowing.objects.filter(myFollowing=request.user , following=user):
        is_following=True
    
    # to display the recent activity
    room_messages = user.message_set.all()
    
    # to display the Topics


    context = {'user':user , 'rooms':rooms ,'is_following' :is_following,
        'room_messages':room_messages , 'user_followers':user_followers ,
          'user_followings':user_followings }
    
    get_topics(request , context)
    return render(request , 'base/profile.html' ,context)

@login_required(login_url='login')
def createRoom(request):
    topics = Topic.objects.all()
    form = RoomForm()
    
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic , created = Topic.objects.get_or_create(name=topic_name)
        # https://youtu.be/PtQiiknWUcI?t=18365  to understand get_of_create() working

        # print("\n\n" ,topic,"\n\n" , created,"\n\n")
        Room.objects.create(
            host = request.user,
            topic = topic,
            name = request.POST.get('name'),
            description = request.POST.get('description')
        )

        return redirect('home')

    context = {'form':form , 'name':'Create','topics':topics}
    return render(request , 'base/room_form.html' ,context)

@login_required(login_url='login')
def updateRoom(request , pk):# here pk = primary key to identify the room
    topics = Topic.objects.all()
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)

    # condition to prevent that other user can not edit the other user's room
    if request.user != room.host:
        return HttpResponse('You are not allowed!!')


    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic , created = Topic.objects.get_or_create(name=topic_name)

        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()
        return redirect('home')

    context={'form':form , 'name':'Update' ,'topics':topics , 'room':room}
    return render(request , 'base/room_form.html' ,context)

@login_required(login_url='login')
def deleteRoom(request , pk):# here pk = primary key to identify the room
    room = Room.objects.get(id=pk)

    # condition to prevent that other user can not delete the other user's room
    if request.user != room.host:
        return HttpResponse('You are not allowed!!')
    
    if request.method == 'POST':
        room.delete()
        return redirect('home')
    return render(request , 'base/delete.html' ,{'obj':room})



@login_required(login_url='login')
def deleteMessage(request , pk):# here pk = primary key to identify the message
    message = Message.objects.get(id=pk)

    

    if request.method == 'POST':
        message.delete()
        return redirect('home')
    return render(request , 'base/delete.html' ,{'obj':message})

@login_required(login_url='login')
def updateUser(request):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST , instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile' , pk=user.id)

    context = {'form':form}
    return render(request , 'base/update_user.html',context)


def topicsPage(request):
    q = request.GET.get('q') 
    if q is None:
        q = ''

    topics = Topic.objects.filter(name__icontains=q)
    context={}

    get_topics(request , context , topics)
    return render(request , 'base/topics_page.html' ,context)


def activityPage(request):
    room_messages = Message.objects.all()
    return render(request , 'base/activity_page.html' , {'room_messages':room_messages})

@login_required(login_url='login')
def followUnfollow(request , pk):
    user = User.objects.get(id=pk)
    following = UserFollowing.objects.filter(myFollowing=request.user , following=user)
    
    if following.count() :
        following.delete()
        UserFollowers.objects.filter(myFollower=user , follower=request.user).delete()
    else:
        UserFollowing.objects.create(myFollowing=request.user , following=user).save()
        UserFollowers.objects.create(myFollower=user , follower=request.user).save()

    return redirect('user-profile' , pk=user.id)

@login_required(login_url='login')
def likeMessage(request , pk): # pk is message id
    message = Message.objects.get(id=pk)
    isLiked = message.likes.filter(id=request.user.id)

    if isLiked:
        message.likes.remove(request.user)
    else :
        message.likes.add(request.user)
    
    return redirect("home")

