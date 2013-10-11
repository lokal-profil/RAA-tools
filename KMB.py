# -*- coding: UTF-8  -*-
##
##Future improvements:
##creator templats
##keep a record of id, author
##
from __future__ import with_statement
from google.appengine.api import files
from google.appengine.ext import blobstore
from poster.encode import multipart_encode
import cgi
import webapp2
import urllib2, urllib
from urllib2 import URLError, HTTPError
from httplib import HTTPException
from xml.dom.minidom import parse
from cookielib import CookieJar

#
class MainPage(webapp2.RequestHandler):
    def get(self):
        ID = self.request.get('ID')
        reason = self.request.get('reason')
        self.response.out.write(Format.header(u'Ange KMB ID'))
        if not len(reason) == 0:
            self.response.out.write(reason)
        else:
            self.response.out.write(u'''Ange ett 14-siffrigt ID. <br/>''')
        self.response.out.write(u'''
              <form action="result" method="post">
                <div><input value="%s" name="ID"></div>
                <div><input type="submit" value="Ange KMB ID"></div>
              </form>''' % ID)
        self.response.out.write(u'''
              <i>För att hitta id-numret är den enklaste metoden att navigera till bildens sida hos KMB.<br/>
                 Url:en innehåller texten "id=" följt av det 14-siffriga nummer som behövs.<br/>
              </i>''')
        self.response.out.write(Format.footer())
#
class KMB(webapp2.RequestHandler):
    def post(self):
        ID = self.request.get('ID').strip()
        self.redirect('/kmb/result?' + urllib.urlencode({'ID': ID}), abort=True)
    def get(self):
        run = True
        ID = self.request.get('ID').strip()
        #ID = '16001000034444'             #no license, copyright="RAÄ"
        #ID = '16000200093942'             #no license, ns5:copyright="Riksantikvarieämbetet", pres:copyright="Kontakta ATA"
        #ID = '16000200060583'             #PD-license, copyright="Utgången upphovsrätt"
        #ID = '16001000212444'             #CC-BY, copyright="RAÄ"
        #ID = '16001000149876'             #Danmark
        if (not len(ID) == 14) or (not ID.isdigit()): #invalid
            self.redirect('/kmb/?' + Format.urlencode({'ID': ID, 'reason': u'Sorry men %s är inte ett 14-siffrigt nummer. Försök igen.' % ID}), abort=True)
        try:
            fil = urllib2.urlopen('http://kulturarvsdata.se/raa/kmb/'+ID)
        except HTTPError, e:
            run = False
            self.response.out.write(Format.header(u'Problem med KMB id: %s' %ID))
            self.response.out.write(u'Servern hos kulturarvsdata.se kunde tyvärr inte leverera datan. Säker på att du angivit rätt id?<br/>')
            self.response.out.write(u'Felkod: %d' % e.code)
            self.response.out.write(Format.footer())
        except HTTPException as e:
            run = False
            self.response.out.write(Format.header(u'Problem med KMB id: %s' %ID))
            self.response.out.write(u'Servern hos kulturarvsdata.se kunde tyvärr inte leverera datan. <br/>')
            self.response.out.write(cgi.escape(str(e)))
            self.response.out.write(Format.footer())
        except URLError, e:
            run = False
            self.response.out.write(Format.header(u'Problem med KMB id: %s' %ID))
            self.response.out.write(cgi.escape(e.reason[0]))
            self.response.out.write(Format.footer())
        else:
            self.response.out.write(Format.header(u'Resultat för KMB-nr: %s' % ID))
            self.response.out.write(u'Objektid: <a href="http://kulturarvsdata.se/raa/kmb/html/%s" target="_blank">%s</a><br/>' % (cgi.escape(ID),cgi.escape(ID)))
            A = {'ID' : ID}
            #convert to xml:
            dom = parse(fil)
            #close file because we dont need it anymore:
            fil.close()
            del fil
            KMB.parser(dom, A)
            if not A['problem'] == None:
                run = False
                self.response.out.write(A['problem'])
                self.response.out.write(Format.footer())
        if run:
            #produce template
            template = KMB.createTemplate(A)
            #produce page
            self.response.out.write('<img src="%s" alt="preview"/><br/>' % A['thumbnail'])
            self.response.out.write(u'''
              <form action="AutoUpload" method="post">
                <input type="hidden" name="ID" value="%s">
                <input type="hidden" name="filename" value="%s - kmb.%s.jpg">
                <input type="hidden" name="desc" value="%s">
                <input type="hidden" name="url" value="%s">
                <div><input type="submit" value="Try Auto Upload"></div>
              </form>''' % (A['ID'], A['namn'], A['ID'], template, A['source']))
            self.response.out.write('or download the full-size image from <a href="'+A['source']+'" target="_blank">here</a> ')
            #generate link to upload
            self.response.out.write(u'''and following is automagically copied into the image description on <a href="https://test.wikipedia.org/w/index.php?title=Special:Upload&uploadformstyle=basic&wpDestFile=%s - kmb.%s.jpg&wpUploadDescription=%s" target="_blank">the upload page</a>:<br/><pre>''' % (A['namn'], A['ID'], urllib.quote(template.encode("utf-8"))))
            #self.response.out.write(u'''and copy the following into the image description on <a href="https://commons.wikimedia.org/w/index.php?title=Special:Upload&uploadformstyle=basic&wpDestFile=%s - kmb.%s.jpg&wpUploadDescription=%s" target="_blank">the upload page</a>:<br/><pre>''' % (A['namn'], A['ID'], urllib.quote(template.encode("utf-8"))))
            self.response.out.write(cgi.escape(template))
            self.response.out.write('</pre>')
            self.response.out.write(Format.footer())
        #done
    #
    @staticmethod
    def parser(dom, A):
        A['problem'] = None
        #tags to get
        tagDict = {'namn': ('ns5:itemLabel', None),           #namn
                   'beskrivning': ('pres:description', None), #med ord
                   'byline' : ('pres:byline', None),          #Okänd, Okänd -> {{unknown}}. kasta om sa "efternamn, fornamn" -> "fornamn efternamn".
                   'motiv': ('pres:motive', None),            #också namn? use only if different from itemLabel
                   'copyright' : ('pres:copyright', None),    #RAÄ or Utgången upphovsrätt note that ns5:copyright can be different
                   'license' : ('ns5:mediaLicense', None),    #good as comparison to the above
                   'source' : ('ns5:lowresSource', None),     #source for image (hook up to download) can I check for highres?
                   'dateFrom' : ('ns5:fromTime', None),
                   'dateTo' : ('ns5:toTime', None),           #datum kan saknas
                   'bildbeteckning': ('pres:idLabel', None),  #bildbeteckning
                   'landskap': ('ns5:provinceName', None),
                   'lan' : ('ns5:countyName', None),
                   'land' : ('ns5:country', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/country#'),
                   'kommun' : ('ns6:municipality', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/municipality#'),
                   'kommunName' : ('ns5:municipalityName', None),
                   'socken' : ('ns6:parish', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/parish#'),
                   'sockenName' : ('ns5:parishName', None),
                   'thumbnail' : ('ns5:thumbnailSource', None)}
        #also has muni, kommun etc. combine some of these (linked to sv.wiki?) into "place"
        #if cc-by then include byline in copyright/license
        for tag in tagDict.keys():
            xmlTag = dom.getElementsByTagName(tagDict[tag][0])
            if not len(xmlTag) ==0:
                if tagDict[tag][1] == None:
                    A[tag] = xmlTag[0].childNodes[0].data.strip('"')
                else:
                    A[tag] = xmlTag[0].attributes[tagDict[tag][1]].value[len(tagDict[tag][2]):]
            else:
                A[tag] = ''
        #do coordinates separately
        xmlTag = dom.getElementsByTagName('georss:where')
        if not len(xmlTag) == 0:
            xmlTag = xmlTag[0].childNodes[0].childNodes[0]
            cs = xmlTag.attributes['cs'].value
            #dec = xmlTag.attributes['decimal'].value
            coords = xmlTag.childNodes[0].data.split(cs)
            if len(coords) == 2:
                A['latitude'] =coords[1][:8]
                A['longitude'] =coords[0][:8]
            else:
                A['problem'] = u'Complain to Lokal_Profil: coord was not a point : %s' % A['ID']
        #do visualizes separately need not be shm/fmi/bbr etc. can be multiple
        A['bbr']=A['fmis']=False
        xmlTag = dom.getElementsByTagName('ns5:visualizes')
        if not len(xmlTag) == 0:
            A['avbildar'] = []
            for x in xmlTag:
                url = x.attributes['rdf:resource'].value
                if url.startswith('http://kulturarvsdata.se/raa/fmi/'):
                    A['fmis']=True
                    crop = len('http://kulturarvsdata.se/raa/fmi/')
                    A['avbildar'].append('{{Fornminne|'+url[crop:]+'}}')
                elif url.startswith('http://kulturarvsdata.se/raa/bbr/'):
                    A['bbr']=True
                    crop = len('http://kulturarvsdata.se/raa/bbr/')
                    num = url[crop:crop+3]
                    typ=''
                    if num == '214':
                        typ = '|b'
                    elif num == '213':
                        typ = '|a'
                    elif num == '212':
                        typ = '|m'
                    A['avbildar'].append('{{BBR|'+url[crop:]+typ+'}}')
                elif url.startswith('http://kulturarvsdata.se/raa/bbra/'):
                    A['bbr']=True
                    crop = len('http://kulturarvsdata.se/raa/bbra/')
                    A['avbildar'].append('{{BBR|'+url[crop:]+'|a}}')
                elif url.startswith('http://kulturarvsdata.se/raa/bbrb/'):
                    A['bbr']=True
                    crop = len('http://kulturarvsdata.se/raa/bbrb/')
                    A['avbildar'].append('{{BBR|'+url[crop:]+'|b}}')
                elif url.startswith('http://kulturarvsdata.se/raa/bbrm/'):
                    A['bbr']=True
                    crop = len('http://kulturarvsdata.se/raa/bbrm/')
                    A['avbildar'].append('{{BBR|'+url[crop:]+'|m}}')
                else:
                    A['avbildar'].append(url)
        #and an attempt at determining caegories
        xmlTag = dom.getElementsByTagName('ns5:itemClassName')
        if not len(xmlTag) == 0:
            A['tagg'] = []
            for x in xmlTag:
                A['tagg'].append(x.childNodes[0].data.strip())
        else:
            A['tagg'] = []
        xmlTag = dom.getElementsByTagName('ns5:itemKeyWord')
        if not len(xmlTag) == 0:
            if len(A['tagg'])==0:
                A['tagg'] = []
            for x in xmlTag:
                A['tagg'].append(x.childNodes[0].data.strip())
        #memory seems to be an issue so kill dom
        del dom, xmlTag
        #create date field (can one exist and the other not?)
        if A['dateFrom'] == A['dateTo']:
            A['date'] = A['dateFrom']
        elif (A['dateFrom'][:4] == A['dateTo'][:4]) and (A['dateFrom'][5:] == '01-01') and (A['dateTo'][5:] == '12-31'):
            A['date'] = A['dateFrom'][:4]
        else:
            A['date']='{{other date|between|'+A['dateFrom']+'|'+A['dateTo']+'}}'
        #rejigg byline
        if (A['byline'] == u'Okänd, Okänd') or (A['byline'] == u'Okänd'):
            A['byline'] = '{{unknown}}'
        elif len(A['byline'])==0:
            A['byline'] = '{{not provided}}'
        else:
            bySplit = A['byline'].split(',')
            if len(bySplit)==2:
                A['byline'] = (bySplit[1]+' '+bySplit[0]).strip()
            elif len(bySplit)==1:
                A['byline'] = bySplit[0]
            else:
                pass
        ##Creator
        #spot correct copyright (don't include name if unknown)
        if len(A['license'])>0:
            trim = 'http://kulturarvsdata.se/resurser/License#'
            A['license'] = A['license'].strip()[len(trim):]
        #if not copyright = RAÄ and if license='' then, this is probably unfree
        if (A['license'] == u'pdmark') or (A['copyright'].strip() == u'Utgången upphovsrätt'):
            A['license'] = u'{{PD-Sweden-photo}}'
        elif (A['license'] == u'by') or (A['copyright'].strip() == u'RAÄ'):
            #consider changing this to AND since there ight be a cc-by image which isn't from RAA.
            #Alternatively have another if inside which checks whethere copyright = RAA
            param=u'}}'
            if (A['byline'] == '{{unknown}}') or (A['byline'] == '{{not provided}}'):
                pass
            else:
                param = u'|%s}}' % A['byline']
            A['license'] = u'{{CC-BY-RAÄ‎%s' %param
        else:
            A['problem'] = u'''
                          Det verkar tyvärr som om licensen inte är fri. Copyright="%s", License="%s".<br/>
                          <small>Om informationen ovan är inkorrekt så informera gärna Lokal_Profil.</small>''' % (A['copyright'],A['license'])
        return A
    #
    @staticmethod
    def createTemplate(A):
        txt =  u'{{Kulturmiljöbild-image\n'
        txt += u'|short title = %s\n' % A['namn']
        txt += u'|original description = %s\n' % A['beskrivning']
        txt += u'|wiki description = '
        if not A['motiv'] == A['namn']:
            txt += u'%s ' % A['motiv']
        if 'avbildar' in A.keys():
            for av in A['avbildar']:
                txt += u'%s ' % av
        txt += u'\n'
        #txt += u'|photographer = '+A['byline']+'\n'
        txt += u'|photographer = {{safesubst:User:Lokal_Profil/nycklar/creators|%s|t}}\n' % A['byline']
        if len(A['land'])==0 or A['land']=='se':
            #kommunTemp
            kommunLink = A['kommunName']
            if not any(A['kommunName'].endswith(x) for x in ('a','o','u',u'å','e','i','y',u'ä',u'ö','s','x')):   #add s if kommun does not end in s or a vowel
                kommunLink += 's'
            kommunLink += ' kommun'
            #end kommunTemp
            txt += u'|depicted place = {{Country|1=SE}}, %s, [[:sv:%s|%s]]' % (A['lan'], kommunLink, A['kommunName'])
            if len(A['socken'])>0:
                txt += u', [[:sv:{{safesubst:User:Lokal_Profil/nycklar/socknar|%s}}|%s (%s)]]\n' % (A['socken'], A['sockenName'], A['landskap'])
            else:
                txt += u'\n'
            #txt += u'|depicted place = Sweden, %s, [[:sv:{{safesubst:User:Lokal_Profil/nycklar/kommuner|%s}}|%s]], [[:sv:{{safesubst:User:Lokal_Profil/nycklar/socknar|%s}}|%s (%s)]]\n' % (A['lan'], A['kommun'], A['kommunName'], A['socken'], A['sockenName'], A['landskap'])
        else:
            txt += u'|depicted place = {{Country|1=%s}}\n' % A['land'].upper()
        txt += u'|date = %s\n' % A['date']
        txt += u'|permission = %s\n' % A['license']
        txt += u'|ID = %s\n' % A['ID']
        txt += u'|bildbeteckning = %s\n' % A['bildbeteckning']
        txt += u'|notes = \n'
        txt += u'}}\n'
        if ('latitude' in A.keys()) and (len(A['latitude'])>0):
            txt += u'{{Object location dec|%s|%s}}' % (A['latitude'],A['longitude'])
        txt += u'\n\n'
        txt += u'{{safesubst:User:Lokal_Profil/nycklar/creators|%s|c}}\n' % A['byline']
        if A['fmis']:
            txt += u'[[Category:Archaeological monuments in %s]]\n' % A['landskap']
            txt += u'[[Category:Archaeological monuments in %s County]]\n' % A['lan']
        if A['bbr']:
            txt += u'[[Category:Protected buildings in Sweden]]\n'
        #must be better to do this via safesubst
        if len(A['tagg']) > 0:
            for tagg in A['tagg']:
                txt += u'{{safesubst:User:Lokal_Profil/nycklar/cats|%s|%s|%s}}\n' % (tagg, A['land'].upper(), A['landskap'])
        return txt
    #
#
class AutoUpload(webapp2.RequestHandler):
    def post(self):
        ID = self.request.get('ID').strip()
        filename = self.request.get('filename').strip()
        desc = self.request.get('desc').strip()
        fileurl = self.request.get('url').strip()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(CookieJar())) #for cookiesupport
        user='<my-user>'
        passw='<my-password>'
        wikiurl = u'https://test.wikipedia.org'
        #wikiurl = u'https://commons.wikimedia.org'
        apiurl = '%s/w/api.php' %wikiurl
        (token, error) = AutoUpload.login(apiurl, user, passw, opener)
        if(token==None):
            self.response.out.write(Format.header(u'Problem med AutoUpload för KMB id: %s' %ID))
            self.response.out.write('Login error: %s' %error)
            self.response.out.write(Format.footer())
        else:
            (blob_key, error) = AutoUpload.fileToBlob(fileurl, filename) #store file as blob in blobstore
            if(blob_key==None):
                self.response.out.write(Format.header(u'Problem med AutoUpload för KMB id: %s' %ID))
                self.response.out.write('File download error: %s' %error)
                self.response.out.write(Format.footer())
            else:
                ffile = blobstore.BlobReader(blob_key)     # Open the blob as a file-like object
                comment = 'API testing'
                #comment = 'KMB upload using tool at lokal-profil.appspot.com/kmb/'
                (success, error) = AutoUpload.upload4(apiurl, filename, ffile, opener, token, desc=desc, comment=comment)
                if success:
                    self.response.out.write(Format.header(u'AutoUpload för KMB id: %s' %ID))
                    self.response.out.write('Success! View the file at  <a href="%s/wiki/File:%s" target="_blank">%s</a><br/>' %(wikiurl,filename,filename))
                else:
                    self.response.out.write(Format.header(u'Problem med AutoUpload för KMB id: %s' %ID))
                    self.response.out.write('AutoUpload failed!<br/>%s<br/>To go back to previous page click <a href="/kmb/result?ID=%s">here</a>.' %(error, ID))
                self.response.out.write(Format.footer())
                #and finally delete the blob from the blob store
                ffile.close()
                files.delete(files.blobstore.get_file_name(blob_key))
    #
    @staticmethod
    def login(apiurl, user, passw, opener):
        '''logs in user to commons and returns an edittoken (or None + error message)'''
        lgname = user
        lgpassword = passw
        error=''
        params = {'action':'login', 'lgname':lgname, 'lgpassword':lgpassword, 'format':'xml'}
        req = urllib2.Request(apiurl, data=urllib.urlencode(params))
        response = opener.open(req)
        dom = parse(response)
        if(len(dom.getElementsByTagName('error'))>0):
            error = dom.getElementsByTagName('error')[0].attributes['info'].value
        else:
            data = dom.getElementsByTagName('login')[0]
            if(data.attributes['result'].value == 'NeedToken'):
                params['lgtoken'] = data.attributes['token'].value
                req = urllib2.Request(apiurl, data=urllib.urlencode(params))
                response = opener.open(req)
                dom = parse(response)
                if(len(dom.getElementsByTagName('error'))>0):
                    error = dom.getElementsByTagName('error')[0].attributes['info'].value
                else:
                    data = dom.getElementsByTagName('login')[0]
                    if(not data.attributes['result'].value == 'Success'):
                        error = data.attributes['result'].value
            elif(data.attributes['result'].value == 'Success'):
                pass
            else:
                error = data.attributes['result'].value
        if(error == ''):
            response = opener.open('%s?action=query&prop=info&intoken=edit&titles=Foo&format=xml' %apiurl)
            dom = parse(response)
            data = dom.getElementsByTagName('page')[0]
            token = data.attributes['edittoken'].value
            return (token,'')
        else:
            return (None, error)
    #
    @staticmethod
    def fileToBlob(fileurl, filename):
        '''Downloads a file from a url and stores it as a blob. Returns blob_key'''
        blob_key=None
        error = ''
        try:
            #Get the file
            imagefile = urllib2.urlopen(fileurl)
        except HTTPError, e:
            error = '[httpError] for %s. Felkod: %d<br/>' %(fileurl,e.code)
        except URLError, e:
            error = '[urlError] for %s. Fel: %s<br/>' %(fileurl,cgi.escape(e.reason[0]))
        else:
            # Create the blobfile
            file_name = files.blobstore.create(mime_type=imagefile.headers['Content-Type'], _blobinfo_uploaded_filename=filename)
            # Open the file and write to it
            with files.open(file_name, 'ab') as f:
                f.write(imagefile.read())
            # Finalize the file. Do this before attempting to read it.
            files.finalize(file_name)
            # Get the file's blob key
            blob_key = files.blobstore.get_blob_key(file_name)
        return (blob_key, error)
    #
    @staticmethod
    def upload(apiurl, filename, desc, fileurl, opener, edittoken):
        '''uploads (via url) a file to commons'''
        error=''
        success = False
        params = {'action':'upload', 'format':'xml', 'filename':filename, 'text':desc, 'comment':'KMB upload using tool at lokal-profil.appspot.com/kmb/', 'token':edittoken, 'url':fileurl}
        req = urllib2.Request(apiurl, data=Format.urlencode(params))
        response = opener.open(req)
        dom = parse(response)
        if(len(dom.getElementsByTagName('error'))>0):
            error = 'File upload error: %s' %dom.getElementsByTagName('error')[0].attributes['info'].value
        else:
            data = dom.getElementsByTagName('upload')[0]
            if(data.attributes['result'].value == 'Success'):
                success = True
            elif(data.attributes['result'].value =='Warning'):
                warning=''
                data2 = data.getElementsByTagName('warnings')[0]
                if(len(data2.attributes.values())>0):
                    warning = data2.attributes.keys()[0]
                elif(data2.firstChild.localName == u'duplicate'):
                    warning = 'duplicate of %s' %data2.firstChild.childNodes[0].childNodes[0].toxml()
                else:
                    warning = data2.firstChild.localName
                error = 'File upload warning: %s' %warning
        return (success, error)
    @staticmethod
    def upload4(apiurl, filename, ffile, opener, edittoken, desc=None, comment=''):
        """Upload a file, requires the "poster" module

        filename - Name of file on wiki
        desc - the initial page content, if the file doesn't already exist on the wiki
        comment - The log comment, used as the inital page content if the file doesn't already exist on the wiki and no desc is given
        fileurl - A URL to get the file from
        ignorewarnings - Ignore warnings about duplicate files, etc.
        watch - Add the page to your watchlist
        edittoken - edittoken for this session
        opener - urlopener containing cookie etc

        """
        error=''
        success = False
        params = {'action':'upload',
            'format':'xml',
            'filename':filename,
            'text':desc,
            'comment':comment,
            'token':edittoken,
            'file':ffile
        }
        (datagen, headers) = multipart_encode(params)
        encodeddata = ''
        for singledata in datagen:
            encodeddata = encodeddata + singledata
        req = urllib2.Request(apiurl, data=encodeddata, headers=headers)
        try:
            response = opener.open(req)
        except HTTPError, e:
            error = '%sError (http) contacting api. Felkod: %d<br/>' %(error,e.code)
        except URLError, e:
            error = '%sError (url) contacting api. Fel: %s<br/>' %(error,cgi.escape(e.reason[0]))
        else:
            dom = parse(response)
            if(len(dom.getElementsByTagName('error'))>0):
                error = u'%sFile upload error: %s<br/>' %(error, dom.getElementsByTagName('error')[0].attributes['info'].value)
            elif(dom.toxml()[:43]=='<?xml version="1.0" ?><!DOCTYPE HTML><html>'):
                error = '%sFile upload error: Something went very wrong... sorry [html returned instead of xml]<br/>' %error
            else:
                data = dom.getElementsByTagName('upload')[0]
                if(data.attributes['result'].value == 'Success'):
                    success = True
                elif(data.attributes['result'].value =='Warning'):
                    warning=''
                    data2 = data.getElementsByTagName('warnings')[0]
                    if(len(data2.attributes.values())>0):
                        warning = data2.attributes.keys()[0]
                    elif(data2.firstChild.localName == u'duplicate'):
                        warning = 'duplicate of %s' %data2.firstChild.childNodes[0].childNodes[0].toxml()
                    else:
                        warning = data2.firstChild.localName
                    error = '%sFile upload warning: %s<br/>' %(error, warning)
        return (success, error)
#
class Format:
    @staticmethod
    def urlencode(aDict):
        '''This ensures that every object of a dict is utf-8 encoded'''
        eDict = {}
        for k, v in aDict.iteritems():
            if isinstance(v, list):              #for lists each object must be encoded
                tmp=''
                for i in v:
                    tmp+='|'+unicode(i).encode('utf-8')
                eDict[k] = tmp
            else:
                eDict[k] = unicode(v).encode('utf-8')
        return urllib.urlencode(eDict)
    @staticmethod
    def header(title):
        txt ='''
          <html>
            <head>
              <title>%s</title>
            </head>
            <body>''' % title
        return txt
    @staticmethod
    def footer():
        txt = '''
              <hr>
              <small>If you have any problems or questions please contact <a href="https://sv.wikipedia.org/wiki/Anv%C3%A4ndardiskussion:Lokal_Profil" target="_blank">Lokal_Profil</a></small>.
            </body>
          </html>'''
        return txt
    #
#

app = webapp2.WSGIApplication([('/kmb/', MainPage),
                               ('/kmb/result', KMB),
                               ('/kmb/AutoUpload', AutoUpload)],
                              debug=True)
