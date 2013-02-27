# Create your views here.  

from django.template import loader, RequestContext
from django.shortcuts import render_to_response, render
from django.core.urlresolvers import reverse
from django.core.context_processors import csrf 
from django.core import exceptions
from django.views.generic import ListView

from agagd_core.models import Games, Members, Tournaments, Ratings
from agagd_core.tables import GameTable, MemberTable, TournamentTable, OpponentTable
from agagd_core.json_response import JsonResponse

from django.http import HttpResponseRedirect
from django.db.models import Q
from django_tables2   import RequestConfig

from datetime import datetime, timedelta 

def index(request):
    game_list = Games.objects.filter(game_date__gte=datetime.now() - timedelta(days=180)).order_by('-game_date')
    table = GameTable(game_list, prefix='games')
    RequestConfig(request).configure(table)
    tourneys = Tournaments.objects.all().order_by('-tournament_date')
    t_table= TournamentTable(tourneys, prefix="tourneys")
    RequestConfig(request, paginate={"per_page": 10}).configure(t_table)
    return render(request, "agagd_core/index.html",
            {
                'table': table,
                'tournaments': t_table,
            }) 

def redirect_to_idx(request):
    return HttpResponseRedirect('/')


#no idea what the right pattern is here; if the request has a member_id param, redirect
#to the member_detail page with that value.  Otherwise, i guess we send them home?
def member_fetch(request):
    context = RequestContext(request)
    if request.method != 'POST':
        return HttpResponseRedirect('/')

    if 'member_id' in request.POST:
        return HttpResponseRedirect(
                    reverse('agagd_core.views.member_detail',
                    args=(request.POST['member_id'],))
                    )

def member_ratings(request, member_id):
    #returns a members rating data as a json dict for graphing
    try:
        player = Members.objects.get(pk=member_id)
        ratings = player.ratings_set.all().order_by('elab_date')
        ratings_dict = [{'sigma': r.sigma,
                'elab_date': r.elab_date,
                'rating': r.rating} for r in ratings]
        #return JsonResponse({'data':ratings_dict, 'result':'ok'}) 
        return JsonResponse(ratings_dict) 
    except:
        return JsonResponse({'result':'error'})

def member_detail(request, member_id):
    game_list = Games.objects.filter(
            Q(pin_player_1__exact=member_id) | Q(pin_player_2__exact=member_id)
            ).order_by('-game_date','round')
    table = GameTable(game_list, prefix="games")
    RequestConfig(request, paginate={"per_page": 20}).configure(table) 

    player = Members.objects.get(member_id=member_id)
    ratings = player.ratings_set.all().order_by('-elab_date')
    if len(ratings) > 0:
        max_rating = max([r.rating for r in ratings])
        last_rating = ratings[0]
    else:
        max_rating = last_rating = None

    opponent_data = {}
    for game in game_list:
        try:
            op = game.player_other_than(player)
            dat = opponent_data.get(op, {}) 
            dat['opponent'] = op
            dat['total'] = dat.get('total', 0) + 1
            dat['won'] = dat.get('won', 0)
            dat['lost'] = dat.get('lost', 0)
            if game.won_by(player):
                dat['won'] += 1
            else:
                dat['lost'] += 1
            opponent_data[op] = dat
        except exceptions.ObjectDoesNotExist:
            print "failing game_id: %s" % game.pk 

    print "opponent tables created ok!"
    opp_table = OpponentTable(opponent_data.values(), player, prefix="opp")
    opp_table.this_player = player
    RequestConfig(request, paginate={"per_page": 10}).configure(opp_table) 
    return render(request, 'agagd_core/member.html',
            {
                'table': table,
                'player': player,
                'rating': last_rating,
                'max_rating': max_rating,
                'num_games': len(game_list),
                'opponents': opp_table
            }) 

def member_search(request):
    queryset = Members.objects.all()
    q = request.GET.get('q') 
    if q is not None and q != "" :
        print "filtering for %r" % q
        queryset = queryset.filter(full_name__icontains=q)
    member_table = MemberTable(queryset)
    RequestConfig(request, paginate={"per_page": 100}).configure(member_table)
    return render_to_response('agagd_core/search_player.html',
            {
                'member_table': member_table,
            })

def member_vs(request, member_id, other_id):
    game_list = Games.objects.filter(
            Q(pin_player_1__exact=member_id, pin_player_2__exact=other_id) |
            Q(pin_player_1__exact=other_id, pin_player_2__exact=member_id),
            ).order_by('-game_date')
    table = GameTable(game_list)
    RequestConfig(request, paginate={"per_page": 20}).configure(table)
    return render_to_response('agagd_core/member.html',
            {
                'table': table,
            }) 

def tournament_detail(request, tourn_code):
    tourney = Tournaments.objects.get(pk=tourn_code)
    #members = set([game.pin_player_1 for game in games] + [game.pin_player_2 for game in games])
    game_table = GameTable(tourney.games_in_tourney.all())
    RequestConfig(request, paginate={"per_page": 20}).configure(game_table)
    return render_to_response('agagd_core/tourney.html',
            {
                'game_table': game_table,
                'tournament': tourney,
            }) 

def tournament_list(request):
    pass

