from __future__ import with_statement
from google.appengine.api import files
from google.appengine.ext import blobstore
from poster.encode import multipart_encode
import urllib2, urllib
from cookielib import CookieJar
from xml.dom.minidom import parse
import webapp2

class AutoUpload(webapp2.RequestHandler):
    def get(self):
        fileurl= self.request.get('fileurl').strip()
        filename=self.request.get('filename').strip()
        #fileurl='url_to_some_file.jpg'
        #filename='Filename_on_wiki.jpg'
        #Download file and store as blob
        blob_key= AutoUpload.fileToBlob(fileurl, filename)
        # Open the blob as a file-like object
        ffile = blobstore.BlobReader(blob_key)
        
        #Now for the wiki bit
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(CookieJar()))
        #user='my-username'
        #passw='my-password'
        user='<my-user>'
        passw='<my-password>'
        apiurl = 'https://test.wikipedia.org/w/api.php'
        #Login and aquire edit token
        (edittoken, success) = AutoUpload.login(apiurl, user, passw, opener)
        
        if not success:
            self.response.out.write('Login failed')
        else:
            #attempt upload
            params = {'action':'upload',
                      'format':'xml',
                      'filename':filename,
                      'text':'a description',
                      'comment':'upload comment',
                      'token':edittoken,
                      'file':ffile
            }
            (datagen, headers) = multipart_encode(params)
            encodeddata = ''
            for singledata in datagen:
                encodeddata = encodeddata + singledata
            req = urllib2.Request(apiurl, data=encodeddata, headers=headers)
            response = opener.open(req)
            dom = parse(response)
            if(len(dom.getElementsByTagName('error'))>0):
                self.response.out.write('Upload error: %s' %dom.getElementsByTagName('error')[0].attributes['info'].value)
            else:
                data = dom.getElementsByTagName('upload')[0]
                if(data.attributes['result'].value == 'Success'):
                    self.response.out.write('Upload is a success')
                else:
                    self.response.out.write('Upload successfully attempted but a warning was raised')
        
        #and finally delete the blob from the blob store
        ffile.close()
        files.delete(files.blobstore.get_file_name(blob_key))
    
    
    @staticmethod
    def fileToBlob(fileurl, filename):
        '''Downloads a file from a url and stores it as a blob. Returns blob_key'''
        #Get the file
        imagefile = urllib2.urlopen(fileurl)
        # Create the blobfile
        file_name = files.blobstore.create(mime_type=imagefile.headers['Content-Type'], _blobinfo_uploaded_filename=filename)
        # Open the file and write to it
        with files.open(file_name, 'ab') as f:
            f.write(imagefile.read())
        # Finalize the file. Do this before attempting to read it.
        files.finalize(file_name)
        # Get the file's blob key
        blob_key = files.blobstore.get_blob_key(file_name)
        return blob_key
    
    @staticmethod
    def login(apiurl, user, passw, opener):
        success = True
        token=None
        params = {'action':'login',
                  'lgname':user, 
                  'lgpassword':passw, 
                  'format':'xml'
        }
        req = urllib2.Request(apiurl, data=urllib.urlencode(params))
        response = opener.open(req)
        dom = parse(response)
        if(len(dom.getElementsByTagName('error'))>0):
            success = False
        else:
            data = dom.getElementsByTagName('login')[0]
            if(data.attributes['result'].value == 'Success'):
                pass
            elif(data.attributes['result'].value == 'NeedToken'):
                params['lgtoken'] = data.attributes['token'].value
                req = urllib2.Request(apiurl, data=urllib.urlencode(params))
                response = opener.open(req)
                dom = parse(response)
                if(len(dom.getElementsByTagName('error'))>0):
                    success = False
                else:
                    data = dom.getElementsByTagName('login')[0]
                    if(not data.attributes['result'].value == 'Success'):
                        success = False
            else:
                success = False
        
        #now get edittoken
        if success:
            response = opener.open('%s?action=query&prop=info&intoken=edit&titles=Foo&format=xml' %apiurl)
            dom = parse(response)
            data = dom.getElementsByTagName('page')[0]
            token = data.attributes['edittoken'].value
        return (token, success)

app = webapp2.WSGIApplication([('/autotest/', AutoUpload)],
                              debug=True)
