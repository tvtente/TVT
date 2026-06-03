// File: menus/static/menus/admin/js/hide_fields.js
// This script dynamically shows/hides form fields in the MenuItem admin based on Link Type.

(function($) {
    $(function() { // Ensure DOM is ready

        var $linkTypeSelect = $('.admin-link-type-select');
        
        var $linkPageField = $('#id_link_page').closest('.form-row, .form-group, .field-link_page'); 
        var $linkCategoryField = $('#id_link_category').closest('.form-row, .form-group, .field-link_category');
        var $linkUrlField = $('#id_link_url').closest('.form-row, .form-group, .field-link_url');
        var $postListTypeField = $('#id_post_list_type').closest('.form-row, .form-group, .field-post_list_type');
        var $dynamicItemsLimitField = $('#id_dynamic_items_limit').closest('.form-row, .form-group, .field-dynamic_items_limit');

        function toggleFields() {
            var selectedLinkType = $linkTypeSelect.val();

            $linkPageField.hide();
            $linkCategoryField.hide();
            $linkUrlField.hide();
            $postListTypeField.hide();
            $dynamicItemsLimitField.hide();

            if (selectedLinkType === 'page') {
                $linkPageField.show();
            } else if (selectedLinkType === 'category') {
                $linkCategoryField.show();
            } else if (selectedLinkType === 'url') {
                $linkUrlField.show();
            } else if (selectedLinkType === 'post_list') {
                $postListTypeField.show();
                $dynamicItemsLimitField.show();
            } else if (selectedLinkType === 'all_blog_categories' || selectedLinkType === 'important_pages') {
                $dynamicItemsLimitField.show();
            }
        }

        $linkTypeSelect.on('change', toggleFields);
        toggleFields();
    });
})(django.jQuery); // Use django.jQuery to ensure compatibility with Django's admin
