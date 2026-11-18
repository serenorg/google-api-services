# ABOUTME: Recorded Google YouTube bodies used by the critical route check.
# ABOUTME: Contains public result data and error bodies without credentials.

# Search: GET https://www.googleapis.com/youtube/v3/search
# part=snippet&q=news&channelId=UC_x5XG1OV2P6uZZ5FSM9Ttw&maxResults=5
# Recorded by python-youtube on 2020-03-15; retrieved 2026-11-18 from:
# https://github.com/sns-sdks/python-youtube/blob/1694c2c91820dde127a1876ee2f16db31c565d7c/testdata/apidata/search/search_videos_by_channel.json
# Quota error: real Google response reported 2024-12-16, retrieved 2026-11-18:
# https://issuetracker.google.com/issues/384276586
# Forbidden: GET https://www.googleapis.com/youtube/v3/search?part=snippet&q=news
# Captured without a key on 2026-11-18 (HTTP 403).

SEARCH_RESPONSE = {'kind': 'youtube#searchListResponse',
 'etag': '"SJZWTG6xR0eGuCOh2bX6w3s4F94/qDAZEJAlbMKs4-6fpruc8u6toc4"',
 'nextPageToken': 'CAUQAA',
 'regionCode': 'US',
 'pageInfo': {'totalResults': 81297, 'resultsPerPage': 5},
 'items': [{'kind': 'youtube#searchResult',
            'etag': '"SJZWTG6xR0eGuCOh2bX6w3s4F94/N6Cmq8y3KhHdFk-mVd7aFwW_U34"',
            'id': {'kind': 'youtube#video', 'videoId': 'LrQWzOkC0XQ'},
            'snippet': {'publishedAt': '2018-10-08T22:51:23.000Z',
                        'channelId': 'UC_x5XG1OV2P6uZZ5FSM9Ttw',
                        'title': 'Code Cleanup and Fixing Pub Versioning in Hacker News App (The '
                                 'Boring Flutter Dev Show, Ep. 8.2)',
                        'description': 'In this first segment, Filip and Emily update the app to '
                                       'pull Hacker News stories live from the Hacker News API, '
                                       'instead of presenting hardcoded stories; they ...',
                        'thumbnails': {'default': {'url': 'https://i.ytimg.com/vi/LrQWzOkC0XQ/default.jpg',
                                                   'width': 120,
                                                   'height': 90},
                                       'medium': {'url': 'https://i.ytimg.com/vi/LrQWzOkC0XQ/mqdefault.jpg',
                                                  'width': 320,
                                                  'height': 180},
                                       'high': {'url': 'https://i.ytimg.com/vi/LrQWzOkC0XQ/hqdefault.jpg',
                                                'width': 480,
                                                'height': 360}},
                        'channelTitle': 'Google Developers',
                        'liveBroadcastContent': 'none'}},
           {'kind': 'youtube#searchResult',
            'etag': '"SJZWTG6xR0eGuCOh2bX6w3s4F94/R5xfc7-ZMB5vjNr4inKwmNeRuWM"',
            'id': {'kind': 'youtube#video', 'videoId': 'lVQ1EKR1v1I'},
            'snippet': {'publishedAt': '2011-09-12T20:55:45.000Z',
                        'channelId': 'UC_x5XG1OV2P6uZZ5FSM9Ttw',
                        'title': 'YouTube&#39;s API and The News',
                        'description': 'On July 20, 2011, YouTube and Link TV hosted a '
                                       'Hacks/Hackers meetup in San Francisco for a first-person '
                                       "look at innovative news projects using YouTube's ...",
                        'thumbnails': {'default': {'url': 'https://i.ytimg.com/vi/lVQ1EKR1v1I/default.jpg',
                                                   'width': 120,
                                                   'height': 90},
                                       'medium': {'url': 'https://i.ytimg.com/vi/lVQ1EKR1v1I/mqdefault.jpg',
                                                  'width': 320,
                                                  'height': 180},
                                       'high': {'url': 'https://i.ytimg.com/vi/lVQ1EKR1v1I/hqdefault.jpg',
                                                'width': 480,
                                                'height': 360}},
                        'channelTitle': 'Google Developers',
                        'liveBroadcastContent': 'none'}},
           {'kind': 'youtube#searchResult',
            'etag': '"SJZWTG6xR0eGuCOh2bX6w3s4F94/hJOHKkFuHJmaRSOr6eukMOQ6QNY"',
            'id': {'kind': 'youtube#video', 'videoId': 'Bud7XR8crWw'},
            'snippet': {'publishedAt': '2018-10-08T22:47:38.000Z',
                        'channelId': 'UC_x5XG1OV2P6uZZ5FSM9Ttw',
                        'title': 'Adding Caching to the Hacker News App (The Boring Flutter '
                                 'Development Show, Ep. 8.3)',
                        'description': 'In this episode of the Boring Show, Filip and Emily '
                                       'showcase a workaround for adding the total comment count, '
                                       'per story, in their Hacker News Reader app.',
                        'thumbnails': {'default': {'url': 'https://i.ytimg.com/vi/Bud7XR8crWw/default.jpg',
                                                   'width': 120,
                                                   'height': 90},
                                       'medium': {'url': 'https://i.ytimg.com/vi/Bud7XR8crWw/mqdefault.jpg',
                                                  'width': 320,
                                                  'height': 180},
                                       'high': {'url': 'https://i.ytimg.com/vi/Bud7XR8crWw/hqdefault.jpg',
                                                'width': 480,
                                                'height': 360}},
                        'channelTitle': 'Google Developers',
                        'liveBroadcastContent': 'none'}},
           {'kind': 'youtube#searchResult',
            'etag': '"SJZWTG6xR0eGuCOh2bX6w3s4F94/9OAtGs7Xc-48ZJrJ20f7sgxOnp4"',
            'id': {'kind': 'youtube#video', 'videoId': 'k_NtkiMAC-o'},
            'snippet': {'publishedAt': '2013-08-14T18:01:59.000Z',
                        'channelId': 'UC_x5XG1OV2P6uZZ5FSM9Ttw',
                        'title': 'YouTube Developers Live: Storyful, The News Agency of The Social '
                                 'Media Age',
                        'description': 'Storfyful is the news agency of the social media age. It '
                                       'provides verified social media content using a mix of '
                                       "human and algorithmic techniques. This week we'll ...",
                        'thumbnails': {'default': {'url': 'https://i.ytimg.com/vi/k_NtkiMAC-o/default.jpg',
                                                   'width': 120,
                                                   'height': 90},
                                       'medium': {'url': 'https://i.ytimg.com/vi/k_NtkiMAC-o/mqdefault.jpg',
                                                  'width': 320,
                                                  'height': 180},
                                       'high': {'url': 'https://i.ytimg.com/vi/k_NtkiMAC-o/hqdefault.jpg',
                                                'width': 480,
                                                'height': 360}},
                        'channelTitle': 'Google Developers',
                        'liveBroadcastContent': 'none'}},
           {'kind': 'youtube#searchResult',
            'etag': '"SJZWTG6xR0eGuCOh2bX6w3s4F94/LS7osmF_lfU6MCsh0sOh-Cetex4"',
            'id': {'kind': 'youtube#video', 'videoId': 'dfweWyVScaI'},
            'snippet': {'publishedAt': '2014-09-03T00:53:44.000Z',
                        'channelId': 'UC_x5XG1OV2P6uZZ5FSM9Ttw',
                        'title': 'Breaking News at 1000ms with Patrick Hamann',
                        'description': 'Patrick is a senior client-side engineer at the Guardian '
                                       'in London where – amongst other things – he is helping to '
                                       'build the next generation of their web platform.',
                        'thumbnails': {'default': {'url': 'https://i.ytimg.com/vi/dfweWyVScaI/default.jpg',
                                                   'width': 120,
                                                   'height': 90},
                                       'medium': {'url': 'https://i.ytimg.com/vi/dfweWyVScaI/mqdefault.jpg',
                                                  'width': 320,
                                                  'height': 180},
                                       'high': {'url': 'https://i.ytimg.com/vi/dfweWyVScaI/hqdefault.jpg',
                                                'width': 480,
                                                'height': 360}},
                        'channelTitle': 'Google Developers',
                        'liveBroadcastContent': 'none'}}]}

QUOTA_RESPONSE = {'error': {'code': 403,
           'message': 'The request cannot be completed because you have exceeded your <a '
                      'href="/youtube/v3/getting-started#quota">quota</a>.',
           'errors': [{'message': 'The request cannot be completed because you have exceeded your '
                                  '<a href="/youtube/v3/getting-started#quota">quota</a>.',
                       'domain': 'youtube.quota',
                       'reason': 'quotaExceeded'}]}}

FORBIDDEN_RESPONSE = {'error': {'code': 403,
           'message': 'Permission denied on the service.',
           'errors': [{'message': 'Permission denied on the service.',
                       'domain': 'global',
                       'reason': 'forbidden'}],
           'status': 'PERMISSION_DENIED',
           'details': [{'@type': 'type.googleapis.com/google.rpc.ErrorInfo',
                        'reason': 'ACCESS_DENIED',
                        'domain': 'googleapis.com',
                        'metadata': {'service': 'youtube.googleapis.com'}},
                       {'@type': 'type.googleapis.com/google.rpc.LocalizedMessage',
                        'locale': 'en-US',
                        'message': 'Permission denied on the service.'}]}}
