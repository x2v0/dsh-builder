import os
path = 'native/system/packages/entry/src/flock.c'
with open(path, 'r') as f:
    content = f.read()
old_code = 'request->error = flock(request->fd, LOCK_EX | LOCK_NB) == 0 ? 0 : errno;'
new_code = 'struct flock fl; fl.l_type = F_WRLCK; fl.l_whence = SEEK_SET; fl.l_start = 0; fl.l_len = 0; request->error = fcntl(request->fd, F_SETLK, &fl) == 0 ? 0 : errno;'
if old_code in content:
    content = content.replace(old_code, new_code)
    if '#include <fcntl.h>' not in content:
        content = content.replace('#include <sys/file.h>', '#include <sys/file.h>\n#include <fcntl.h>')
    with open(path, 'w') as f:
        f.write(content)
    print('[+] flock.c patched.')
