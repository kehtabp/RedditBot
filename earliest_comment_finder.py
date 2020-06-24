from datetime import datetime
import backoff
import requests
from fuzzywuzzy import fuzz

list_of_candidates = [["Paiev"],
                      ["city-of-stars", "City of stars", "city\\_of\\_stars", "city_of_stars"],
                      ["gcnHNYqvzB637fyQvQDt"],
                      ["2015_BCS_ORANGE_BOWL", "2015_BSC_ORANGE_BOWL", "2015_BSC_ORANGE", "2015\\_BCS\\_Orange\\_Bowl",
                       "2015_bcs_orange_bowl", "2015_BCS_Orange_Bowl", "2015 bsc orange bowl", "2015 back orange bowl",
                       "BCS Orange bowl"],
                      ["Tryingtolearn_1234", "Trying to learn 1234"],
                      ["Ericabneri"],
                      ["The-Magenetic-Dude"],
                      ["Triopsi"],
                      ["Atopix", 'atopix'],
                      ["Zilong67"],
                      ["MrLegilimens", "legilimens", "Mr leglimens"],
                      ["OldWolf2"],
                      ["Astrath"],
                      ["CoolestBlue"],
                      ["LadyLatteMotif", 'ladylattemotif', "lady latte motif"],
                      ["nhum"],
                      ["Mobile-Escape"],
                      ["Conalfisher"],
                      ["Tactics14", "Tactics 14"],
                      ["Powerchicken"],
                      ["TimDual", "timdual"],
                      ["Fifatastic"],
                      ["Juxxapose", "juxtaposed", "Juxxtapose", "jussxtapose_", "Juxapoose", "Juxxtapose\_"],
                      ["FreudianNipSlip123", "FreudianNipslip", "FreudiuanNipSlip"],
                      ["SWAT__ATTACK", "SWAT\\_\\_ATTACK", "SWAT\\_ATTACK", "Swat attack", "Swat__Attack"], ]


@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException)
def get_pushshift_data(user):
    pd_url = f'https://api.pushshift.io/reddit/search/comment/?size=1&before=14d&subreddit=chess&author={user}'
    # print(pd_url)

    r = requests.get(pd_url)
    if r.status_code != 200:
        raise requests.exceptions.RequestException('API response: {}'.format(r.status_code))

    data = r.json()
    return data['data']


def alternative_spellings(body, candidate, user):
    best_ratio = 0
    best_candidate = ""
    debug_string = ""
    for spelling in candidate:
        ratio = fuzz.partial_ratio(body, spelling)
        if ratio > best_ratio:
            best_ratio = ratio
            best_candidate = spelling
        if ratio >= 80:
            return 1

    if best_ratio > 45:
        debug_string += "-------------Close Match------------\n"
        debug_string += f"User: {user}, Candidate:{best_candidate}, Match: {best_ratio}\n"
        debug_string += "-------------BODY BEGIN-------------\n"
        debug_string += body + "\n"
        debug_string += "------------------------------------\n"

    return [0, debug_string]


def get_authors():
    debug_string = ""
    reddit_prefix = 'https://www.reddit.com'
    election_url = "https://api.pushshift.io/reddit/comment/search?link_id=haheq4&size=500"
    r = requests.get(election_url)
    if r.status_code != 200:
        raise requests.exceptions.RequestException('API response: {}'.format(r.status_code))

    data = r.json()['data']
    candidates_string = "\t".join([candidate[0] for candidate in list_of_candidates])
    print(f'Username\tVote link\tDate of the first qualifying comment\tURL for the comment\t{candidates_string}')
    sums = "\t\t\t\t=SUM(E3:E999)\t=SUM(F3:F999)\t=SUM(G3:G999)\t=SUM(H3:H999)\t=SUM(I3:I999)\t=SUM(J3:J999)\t=SUM(" \
           "K3:K999)\t=SUM(L3:L999)\t=SUM(M3:M999)\t=SUM(N3:N999)\t=SUM(O3:O999)\t=SUM(P3:P999)\t=SUM(Q3:Q999)\t=SUM(" \
           "R3:R999)\t=SUM(S3:S999)\t=SUM(T3:T999)\t=SUM(U3:U999)\t=SUM(V3:V999)\t=SUM(W3:W999)\t=SUM(X3:X999)\t=SUM(" \
           "Y3:Y999)\t=SUM(Z3:Z999)\t=SUM(AA3:AA999)\t=SUM(AB3:AB999) "
    print(sums)
    for top_level_comment in [x for x in data if x['parent_id'] == 't3_haheq4']:
        author = top_level_comment['author']

        body = top_level_comment['body']
        debug_candidate_string = ""
        voted_for_string = ""
        for candidate in list_of_candidates:

            result = alternative_spellings(body, candidate, author)
            if result == 1:
                voted_for_string += "1\t"
                debug_candidate_string += candidate[0] + ", "
            else:
                voted_for_string += "0\t"
                debug_string += result[1]
        debug_string += f"{author} final choices: {debug_candidate_string}\n"

        permalink = f"{reddit_prefix}{top_level_comment['permalink']}"
        comments = get_pushshift_data(author)

        for comment in comments:
            date = datetime.fromtimestamp(comment['created_utc'])
            comment_url = f'{reddit_prefix}{comment["permalink"]}'
        print(
            f'{author}\t=HYPERLINK("{permalink}","vote")\t{date}\t=HYPERLINK("{comment_url}","qualifying comment")\t{voted_for_string}')
    return debug_string


print(get_authors())
