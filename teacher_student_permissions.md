# Teacher & Student Permissions Summary

This document summarizes the main permissions for teachers and students in the system, based on their `access_level`.

## Teacher Permissions

| access_level | Permissions                                                                 |
|--------------|-------------------------------------------------------------------------------|
| 2            | - View/search/download/preview theses<br>- View courses                      |
| 3            | - All of level 2<br>- Upload theses (subject to review before visible to org) |

**Notes:**
- Teachers with access_level < 3 cannot upload theses.
- Uploaded theses by teachers require review (is_check=True) before being visible to others.

## Student Permissions

| access_level | Permissions                                                                 |
|--------------|-------------------------------------------------------------------------------|
| 1            | - View/search/preview theses<br>- View courses                               |
| 2            | - All of level 1<br>- Download/purchase theses (if quota is sufficient)<br>- Manage courses (if applicable) |

**Notes:**
- Students with access_level < 2 cannot download/purchase theses.
- All students can search and preview theses within their permission scope.

---

For further customization or more granular permission control, please refer to the codebase or contact the system administrator.
