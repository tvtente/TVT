from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0005_alter_page_is_homepage_page_unique_active_homepage"),
        ("widgets", "0009_widget_top_tag_count_and_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="widget",
            name="page_filter",
            field=models.ForeignKey(
                blank=True,
                help_text="The page displayed by the Page Card widget.",
                null=True,
                on_delete=models.SET_NULL,
                to="pages.page",
                verbose_name="Featured Page (optional)",
            ),
        ),
        migrations.AlterField(
            model_name="widget",
            name="widget_type",
            field=models.CharField(
                choices=[
                    ("recent_posts", "Recent Blog Posts"), ("most_viewed_posts", "Most Viewed Blog Posts"),
                    ("most_commented_posts", "Most Commented Blog Posts"), ("blog_categories", "Blog Category List"),
                    ("featured_tags", "Featured Tags"), ("editor_picks_posts", "Editor's Picks (Blog Posts)"),
                    ("post_grid_recent", "Post Grid: Recent Posts"), ("post_grid_category", "Post Grid: Category"),
                    ("post_grid_popular", "Post Grid: Most Viewed"), ("post_grid_commented", "Post Grid: Most Commented"),
                    ("post_grid_editor", "Post Grid: Editor's Picks"), ("post_grid_top_rated_today", "Post Grid: Top Rated Today"),
                    ("post_grid_top_rated_week", "Post Grid: Top Rated This Week"), ("post_grid_most_favorited", "Post Grid: Most Favorited"),
                    ("post_grid_community_picks", "Post Grid: Community Picks"), ("post_grid_top_tags", "Post Grid: Top Tags"),
                    ("post_intent_reflection", "Intent: For Reflection"), ("post_intent_quick_reads", "Intent: Quick Reads"),
                    ("post_intent_wellbeing", "Intent: Well-being"), ("post_intent_debate", "Intent: Debate Starters"),
                    ("post_carousel", "Post Carousel"), ("post_carousel_commented", "Post Carousel: Most Commented"),
                    ("post_carousel_viewed", "Post Carousel: Most Viewed"), ("hero_carousel", "Hero Carousel"),
                    ("book_grid_recent", "Book Grid: Recent Books"), ("publication_grid_recent", "Publication Grid: Recent Publications"),
                    ("page_card", "Page Card"), ("user_directory", "User Directory"), ("testimonials", "Testimonials"),
                ],
                max_length=50,
                verbose_name="Widget Type",
            ),
        ),
    ]
