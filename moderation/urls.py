from django.urls import path

app_name = 'moderation'

from .views import (
    post_comment_view,
    my_comments_view,
    flagged_comments_view,
    give_feedback_view,
    review_content_view,
    manage_slang_words,
    delete_slang_word,
)

urlpatterns = [
    path('post/', post_comment_view, name='post_comment'),
    path('mine/', my_comments_view, name='my_comments'),
    path('flagged/', flagged_comments_view, name='flagged_comments'),

    path('feedback/<uuid:result_id>/', give_feedback_view, name='give_feedback'),
    path('review/<uuid:content_id>/', review_content_view, name='review_content'),

    path('slang-words/', manage_slang_words, name='manage_slang'),
    path('slang-words/<uuid:word_id>/delete/', delete_slang_word, name='delete_slang_word'),
]
