# Transcripts

There’s a problem that we need to solve. With multiple transcripts and multiple audio/video files, we need to make sure that the selected transcript correctly identifies the time markers for the playing audio. Example: God resource includes the singing before the service starts. allthepreaching does not. So there’s an extra 40 minutes of the video / transcript. If I’m playing an audio from all the preaching, and I’m looking at a transcript from God resource, the audio I am hearing and the transcript I am looking at will be 40 minutes displaced. Brainstorm how we can solve this problem. We need to either A pair the transcript and video/audio sources to always match, or B smartly identity the starting point of the video and match it with the starting point of the transcript. Maybe we could process a small chunk of the audio file for a phrase, find out where that phrase occurs in the transcript, and then match it up? Or we could use a smart approach like working backwards from the ending time to the starting time. Meaning the Sermons may have different start times, one starts with singing in the other starts with preaching, but they should end with roughly the same phrase. After the sermon finishes, then there’s the prayer and they both end with amen. So the hour long sermon and the hour And 40 minute long sermon, I could discover roughly where the hour and 40 minute long sermon starts by subtracting the hour long sermon duration from the hour and 40 minute long sermon, duration, and that should roughly get me to the start of the sermon. But I would still want some kind of algorithm to get to the exact time point. Cause it may still be a few minutes offset. So maybe we could process the few minutes around the starting of God resource videos to figure out where the actual beginning of the preaching is? I would also like when God Resource is selected as the source, for the video to jump to the start of the preaching be default instead of the songs. This requires auto-detection. The problem is that a lot of solutions I have seen require GPUs to be rented for trascript jobs. Is there a way to do auto detection of the sermon start when processing new sermons without renting GPUs?

# misc

- [ ] In most of FWBC sermons the source 2 says Web but actually it should say X. Since it’s x.com.
- [ ] Source 1 for videos say HLS but it should say “God Resource” if it was crawled from God Resource.
- [ ] mp3 should say All The Preaching or Church Website (faithfulwordbaptist.org) if it was take from that. Basically identity the source, not the codec.
- [ ] 2 Kings 6 is missing the allthepreaching mp3 and video source. https://www.allthepreaching.com/video/10012129 — why was this missed? All the preaching is a really great resource because it has the video, audio, AND transcript.
- [ ] Sleep timer should show a countdown of how much time is left until the audio is automatically stopped.
- [ ] Does the upload audio upload the audio to my own website?
- [ ] Marrying someone forbidden by parents has a YouTube link that is dead, so instead of showing artwork it shows a dead YouTube image. Please display the artwork even if the YouTube link is dead. 
- [ ] In most cases I am seeing two loading screens one after another directly. Like when I refresh the page, I two two separate loading screens. This is wrong. It should be one congruent loading screen.




The displayed transcript should be picked based on the audio that is playing

# Preaching Links

Reminder that if the speaker does not match the main preacher of the church, you may need to search the sermon title + speaker name to find the matching video on all the preaching. Write that into the algorithm. 

## First Works Baptist Church

1. Church Website: https://www.fwbcla.org/sermons
2. God Resource: https://godresource.com/c/first-works-baptist-church?sort=newest
3. All The Preaching: https://pastormejiasermons.allthepreaching.com/index.php

## Stedfast Baptist Church

1. Church Website: https://stedfastkjv.com/preaching
2. God Resource: https://godresource.com/c/stedfast
3. All The Preaching: https://allthepreaching.com/preacher/Pastor%20Jonathan%20Shelley

## Anchor Baptist Church

1. Church Website: https://anchorkjv.com/beliefs (no authoritative list of sermons - use algorithm to smartly piece together the list of sermons from non authoritative sources below)
2. YouTube: https://youtube.com/@anchorbaptistchurchokc?si=IvNW2buW_0MWXq_p
3. Rumble: https://rumble.com/c/c-6834379/videos
4. God Resource: https://godresource.com/c/anchor
5. All The Preaching: https://allthepreaching.com/preacher/Pastor%20Dillon%20Awes


## Sure Foundation Baptist Church

1. Church Website: https://www.sfbcindy.com/preaching.html
2. YouTube: https://youtube.com/@sfbcseattle1?si=_rjjej5_C9ae8c7H
3. All The Preaching: https://allthepreaching.com/preacher/Pastor%20Aaron%20Thompson

## John Piper

1. Desiring God — Messages (Primary / authoritative sermon archive): https://www.desiringgod.org/messages
2. Desiring God — Podcasts (Primary / official podcast directory; includes the classic-sermon feed): https://www.desiringgod.org/podcasts
3. Desiring God — YouTube (Primary-adjacent / official video distribution): https://www.youtube.com/@desiringGod
4. Messages by Desiring God — Apple Podcasts (Secondary distribution endpoint): https://podcasts.apple.com/us/podcast/messages-by-desiring-god/id196050704

> Desiring God is the authoritative institutional home for John Piper's message archive, with individual message pages typically serving as the best canonical record for title, date, Scripture, transcript, audio, and/or video. The site explicitly identifies its messages collection as home to messages from Piper, and its podcast directory identifies classic sermons as an official feed. [5][6]

Don’t import other speakers besides John Piper for these ones. 


## William Lane Craig

1. Reasonable Faith — Media (Primary / authoritative media index): https://www.reasonablefaith.org/media/
2. Reasonable Faith — Videos (Primary / official videos, including lectures, debates, talks, interviews, and clips): https://www.reasonablefaith.org/videos/
3. Reasonable Faith — Podcasts (Primary / official podcast index): https://www.reasonablefaith.org/podcasts/
4. Reasonable Faith — YouTube (Primary-adjacent / official video distribution): https://www.youtube.com/@ReasonableFaithOrg
5. Dr Craig Videos — YouTube (Official secondary/clip channel): https://www.youtube.com/@DrCraigVideos
6. Reasonable Faith — Spotify (Secondary podcast distribution): https://open.spotify.com/show/55RPDUm9fOQXHu2sjNqcuh
7. LightSource — Reasonable Faith (Secondary / syndicated sermon-video archive): https://www.lightsource.com/ministry/reasonable-faith/

> Use Reasonable Faith as canonical. It centrally organizes Craig's debates, lectures, talks, interviews, videos, and podcasts; the two YouTube channels are useful redundancy, but canonicalize against the Reasonable Faith media item whenever a corresponding page exists. [8][10][17][19]


Be sure to separate different series into different series. For example he has a defenders podcast that has https://www.reasonablefaith.org/podcasts/defenders-podcast-series-1 with multiple “The Doctrine of God” “The Doctrine of Man” etc which can be seasons within the defenders series 1 series. 

Likewise there is series 2: https://www.reasonablefaith.org/podcasts/defenders-podcast-series-2

And many more. Smartly figure out how to crawl all of these (most are dead not live and do not require a cron to check for updates).

## Francis Chan

Classic sermons: https://www.crazylove.org/messages?before=2015&sort=oldest#results
Recent sermons: https://www.crazylove.org/messages?sort=newest#results

## Rob Bell

1. Rob Bell Official Website (Primary / authoritative home for current work and RobCast): https://robbell.com/
2. RobCast (Primary / official podcast feed; resolve and store its RSS/feed URL from the official site): https://robbell.com/
3. Rob Bell — YouTube (Primary-adjacent / official video channel): https://www.youtube.com/@robbell
4. Mars Hill Bible Church — Sermon Archive (Historical primary-source target, if an accessible first-party archive/feed can be located)
5. RobCast — Apple Podcasts (Secondary podcast distribution; discover the current canonical listing from the official RobCast page)
6. RobCast — Spotify (Secondary podcast distribution; discover the current canonical listing from the official RobCast page)

> Rob Bell does not appear to maintain a single, complete public “sermons” archive comparable to Desiring God or Gospel in Life. Treat robbell.com and RobCast as authoritative for current material; model historical Mars Hill sermons separately from current talks/podcast episodes rather than pretending they are one continuous, authoritative sermon corpus. The official site specifically presents RobCast episodes, events, books, and films. [15]


## Jack Hyles

1. First Baptist Church of Hammond (Primary institutional / historical church source): https://www.fbchammond.com/
2. First Baptist Church of Hammond — History (Primary evidence of Hyles's 1959–2001 pastorate; not a comprehensive sermon archive): https://www.fbchammond.com/history/
3. Jack Hyles Home Page (Primary-adjacent / legacy site containing free books and sermon texts): https://www.jackhyles.com/
4. Jack Hyles Library (Primary-adjacent / dedicated legacy preservation library): https://www.jackhyleslibrary.com/
5. Jack Hyles Library — YouTube (Primary-adjacent / major audio-video sermon source): https://www.youtube.com/@JackHylesLibrary
6. SermonAudio — Jack F. Hyles (Secondary / archive and streaming source): https://www.sermonaudio.com/speakers/5230/sermons
7. SermonIndex — Jack Hyles (Secondary / curated archive): https://sermonindex.net/speakers/jack-hyles/
8. Preach The Bible: Classics — Jack Hyles (Secondary / curated archive): https://classics.preachthebible.org/tag/jack-hyles/
9. Baptist City — Jack Hyles (Secondary / legacy archive, including sermon PDFs): https://www.baptist-city.com/

> There is no obvious current official FBCH master archive covering Hyles's full preaching ministry. Treat FBCH as the authoritative church/historical identity source, then make Jack Hyles Library and jackhyles.com your preferred media/text ingest sources. Use SermonAudio, SermonIndex, Preach The Bible, and Baptist City for gap discovery and alternate encodes. FBCH confirms Hyles served as pastor from 1959–2001; Jack Hyles Library publicly identifies itself as a source for audio sermons, video sermons, and handwritten sermon materials. [34][35][40][42]


## Timothy Keller

1. Timothy Keller Official Website (Primary / authoritative directory): https://timothykeller.com/
2. Gospel in Life — All Resources (Primary / authoritative searchable sermon and talk archive): https://gospelinlife.com/all-resources/
3. Gospel in Life — Sermons and Resources (Primary / official ministry home): https://gospelinlife.com/
4. Gospel in Life — YouTube (Primary-adjacent / official video distribution): https://www.youtube.com/@GospelinLife
5. Gospel in Life Podcast (Primary-adjacent / official podcast distribution; resolve and store current RSS/feed URL from Gospel in Life)
6. Timothy Keller MP3 Sermon Archive on USB (Official paid complete-audio archive, September 1989–June 2017): https://gospelinlife.com/timothy-keller-mp3-sermon-archive/
7. Redeemer Presbyterian Church / Redeemer Churches and Ministries (Historical primary church context; use for original Redeemer-specific records): https://www.redeemer.com/
8. Logos / Verbum — Timothy Keller Sermon Archive (Secondary paid transcript archive): https://verbum.com/product/17902/timothy-keller-sermon-archive-1989-2011

> Gospel in Life is the main authoritative public archive to crawl. It identifies itself as the resource site for Timothy Keller and Redeemer Churches and Ministries, provides searchable resources by sermon/series/topic/Scripture, and offers a complete official MP3 collection of more than 1,550 sermons preached at Redeemer from September 1989 through June 2017. The paid USB archive is audio-only, so keep it as a catalog/availability source rather than assuming equivalent public video or transcript coverage. [21][23][26][29]


## Grace Baptist Church 

1. Church Website:
2. God Resource:
3. All The Preaching: