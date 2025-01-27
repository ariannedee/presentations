import django_filters
import graphene
from django.contrib.auth.models import User
from django.db.transaction import atomic
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from goals.models import Task, Goal


class TaskNode(DjangoObjectType):
    pk = graphene.Int()

    @graphene.resolve_only_args
    def resolve_pk(self):
        return self.pk

    class Meta:
        model = Task
        interfaces = (relay.Node,)


class GoalNode(DjangoObjectType):
    progress = graphene.Float(description='The average task progress')
    pk = graphene.Int()

    @graphene.resolve_only_args
    def resolve_pk(self):
        return self.pk

    class Meta:
        model = Goal
        interfaces = (relay.Node,)
        filter_fields = ['name']


class OwnerNode(DjangoObjectType):
    full_name = graphene.String()

    @graphene.resolve_only_args
    def resolve_full_name(self):
        return u'{} {}'.format(self.first_name, self.last_name)

    class Meta:
        interfaces = (relay.Node,)
        model = User


class GoalFilter(django_filters.FilterSet):
    # Do case-insensitive lookups on 'name'
    name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Goal
        fields = ['name']


class Query(graphene.ObjectType):
    goals = DjangoFilterConnectionField(GoalNode, filterset_class=GoalFilter)


class TaskInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    starting_value = graphene.Float(default_value=0)
    target_value = graphene.Float(default_value=100)


class GoalInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    tasks = graphene.List(TaskInput)


class CreateGoal(graphene.Mutation):
    class Input(object):
        goal = GoalInput(required=True)

    goal = graphene.Field(GoalNode)

    @atomic
    def mutate(self, args, context, info):
        owner = context.user
        goal_data = args['goal']
        name = goal_data['name']
        goal = Goal.objects.create(owner=owner, name=name)
        for kr_data in goal_data.get('tasks', []):
            kr = Task(goal=goal, name=kr_data['name'])
            if 'starting_value' in kr_data:
                kr.starting_value = kr_data['starting_value']
                kr.current_value = kr.starting_value
            if 'target_value' in kr_data:
                kr.target_value = kr_data['target_value']
            kr.save()
        return CreateGoal(goal=goal)


class UpdateTask(graphene.Mutation):
    class Input(object):
        pk = graphene.Int(required=True)
        current_value = graphene.Float(required=True)

    goal = graphene.Field(GoalNode)

    @atomic
    def mutate(self, args, context, info):
        kr = Task.objects.get(pk=args['pk'])
        current_value = args['current_value']
        kr.current_value = current_value
        kr.save()
        return UpdateTask(goal=kr.goal)


class Mutation(graphene.ObjectType):
    create_goal = CreateGoal.Field(description='Create a new goal')
    updateTaskProgress = UpdateTask.Field()

schema = graphene.Schema(
    query=Query,
    mutation=Mutation
)
