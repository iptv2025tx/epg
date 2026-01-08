# Combined EPG

Auto-updated daily EPG (Electronic Program Guide) combining multiple sources.

## EPG URL

Use this URL in your IPTV app:

```
https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/epg.xml
```

## Sources Included

- **USA**: usa1-5 (US channels)
- **UK**: unitedkingdom1-5 (Sky Sports, BBC, ITV, etc.)
- **Sports**: sports1-3 (International sports channels)
- **Canada**: canada1-2
- **Ireland**: ireland1
- **Australia**: australia1-2

Data sourced from [globetvapp/epg](https://github.com/globetvapp/epg).

## Setup Your Own

1. Create a new GitHub repository
2. Copy all files from this folder to your repo
3. Go to Settings > Actions > General
4. Enable "Read and write permissions" under "Workflow permissions"
5. Go to Actions tab and run "Update Combined EPG" manually
6. The workflow will run daily at 4:00 AM UTC automatically

## Manual Update

```bash
python combine_epg.py --output epg.xml
```

## Last Updated

Check the commit history for the latest update time.
