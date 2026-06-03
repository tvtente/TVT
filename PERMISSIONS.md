# Tavata CMS: User Roles and Permissions

This document outlines the user groups, roles, and their specific permissions within the Tavata CMS platform. This structure is designed to provide granular control over content management and site administration.

---

## User Roles Overview

Our system is built upon Django's built-in authentication and permissions framework. Users are assigned to **Groups**, and each group has a specific set of permissions that define what its members can do in the Django admin panel.

### 1. **Superadmin**
- **Purpose:** The root user with absolute power. This role is for core developers and system architects.
- **Implementation:** Any user with the `is_superuser` flag set to `True`.
- **Permissions:**
  - Unrestricted access to all models and settings across the entire project.
  - Can create, manage, and delete a todos los demás usuarios, incluidos otros Superadmins.
  - This role bypasses all standard permission checks.

### 2. **Administrator**
- **Group Name:** `Administrator`
- **Purpose:** Manages the day-to-day operations of the site, including user management and global settings, without having access to server-level code.
- **Permissions:**
  - **Full Control** (`add`, `change`, `delete`, `view`) over:
    - User Accounts (`accounts.User`, `accounts.Profile`)
    - User Groups (`auth.Group`) - Can assign users to other roles.
  - **Full Control** over site-wide configuration:
    - `site_settings.SiteConfiguration` (Paginación, Caching, etc.)
    - `menus.Menu`, `menus.MenuItem`
    - `widgets.WidgetZone`, `widgets.Widget`
  - **Essentially, has all permissions EXCEPT `is_superuser` access.**

### 3. **Editor**
- **Group Name:** `Editor`
- **Purpose:** The primary content lead, responsible for creating, publishing, and managing all blog-related content.
- **Permissions:**
  - **Full Control** over the `blog` app:
    - `blog.Post`
    - `blog.PostCategory`
  - **Can review and edit** existing static pages for corrections, but cannot create or delete them:
    - `pages.Page` (`change`, `view` permissions only)

### 4. **Page Manager (or "Revisor")**
- **Group Name:** `Page Manager`
- **Purpose:** Manages the site's "evergreen" or static content, such as "About Us," "Contact," and legal pages.
- **Permissions:**
  - **Full Control** over the `pages` app:
    - `pages.Page`
    - `pages.Category` (Page Categories)

### 5. **Moderator**
- **Group Name:** `Comment Moderator`
- **Purpose:** Responsible for community management, ensuring a healthy and spam-free discussion environment.
- **Permissions:**
  - **Manages user-submitted content:**
    - `blog.Comment` (`change` to approve/unapprove, `delete`, `view`)
    - `contact.ContactMessage` (`change` to mark as read/set priority, `delete`, `view`)
  - This role **does not** have permission to create or edit primary site content like posts or pages.

### 6. **Author (Future Implementation)**
- **Purpose:** Can create and manage their *own* draft posts but cannot publish them directly. This requires custom logic in `ModelAdmin`. (To be implemented).

### 7. **Subscriber (Standard User)**
- **Purpose:** The base registered user of the community.
- **Permissions:**
  - **Zero permissions** in the Django admin panel.
  - Their "permissions" are on the front-end: leaving comments under their own name, editing their profile, etc.

---
*This document should be updated whenever new roles are added or existing permissions are modified.*