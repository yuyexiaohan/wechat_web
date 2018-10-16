from django.shortcuts import render
from django.http import HttpResponse
import requests
import time, re, json
from bs4 import BeautifulSoup


QCODE = None
CIIME = None
TIP = 1 # 未扫码的就是默认未1
TICKET_DICT = {}
USER_INIT_DICT = {}   # 用户信息
ALL_COOKIE_DICT = {}


def login(request):
	"""1.模拟微信登录"""
	global CIIME
	global QCODE
	CIIME = time.time ()
	response = requests.get(
		url='https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&fun=new&lang=zh_CN&_=%s' % CIIME
	)
	# print(response.text)
	# window.QRLogin.code = 200; window.QRLogin.uuid = "oYFblLzORg==";
	end_url = re.findall('uuid = "(.*)";', response.text)[0]
	QCODE = end_url
	context ={
		'end_url': end_url
	}
	return render(request, 'wechat/login.html', context=context)


def check_login(request):
	"""2.当扫码是，ajax响应"""
	# 从微信网页版看一直响应的peng...的url：
	# 'https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=YYstHORByw==&tip=0&r=-2006687458
	# &_=1539604954051'
	# 'https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=YZxlS4tj6w==&tip=0&r=-2006127153
	# &_=1539604393727'
	# 当url的（QCODE）错误时，直接进行信息的传递，不等待
	global TIP
	r1 = requests.get(
		url='https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=%s&tip=%s&r=-2006127153&_=%s'
		    % (QCODE, TIP, CIIME)
	)
	print('r1:', r1.text)
	# 页面/login刷新时，打印是window.code=408;
	# 扫码后，但会的是window.code=201。
	# 打印结果：'r1: window.code=201;window.userAvatar = 'data:img/jpg;base64,
	# /9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAoHBwgHBgoICAgLCgoLDhgQDg0NDh0VFhEYIx8lJCIfIiEmKzcvJik0KSEiMEExNDk7Pj4+
	# JS5ESUM8SDc9Pjv+....;'
	# 所以可以对这个进行判断：
	ret = {'code': 408, 'data': None}
	if 'window.code=408' in r1.text:
		print('无人扫码状态！')
		return HttpResponse(json.dumps(ret))
	elif 'window.code=201' in r1.text:
		ret['code'] = 201
		avatar = re.findall("window.userAvatar = '(.*)';", r1.text)[0]
		ret['data'] = avatar
		TIP = 0
		return HttpResponse(json.dumps(ret))

	elif 'window.code=200' in r1.text:
		"""200时的返回文件：
		window.code=200;
		window.redirect_uri="https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?
		ticket=AVMHz92NJ5XLz50gDi2fyns8@qrticket_0&uuid=IaTszuUoHg==&lang=zh_CN&scan=1539610356";
		"""
		# 获取登录成功后的cookies并更新全局变量
		ALL_COOKIE_DICT.update(r1.cookies.get_dict())
		print('**r1.text**:', r1.text)
		# 注意正则中的标点符合，匹配内容区分单双引号，返回列表
		redirect_uri = re.findall('window.redirect_uri="(.*)";', r1.text)[0]
		print('redirect_uri:',redirect_uri)     # 打印查看
		"""# 打印结果
		redirect_uri: https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage?ticket=AZhGQ6BJ2R8YuwYzFazcT7Wu
		@qrticket_0&uuid=oZs9xUVwmQ==&lang=zh_CN&scan=1539614002
		"""
		# 返回的url的返回中增加了''&fun=new&version=v2''这个部分，这里要手动添加
		redirect_uri = redirect_uri + '&fun=new&version=v2' # ？失败的url

		# 获取凭证
		r2 = requests.get(url=redirect_uri)     #
		soup = BeautifulSoup(r2.text, 'html.parser')
		for tag in soup.find('error').children:
			TICKET_DICT[tag.name] = tag.get_text()
		print('TICKET_DICT:',TICKET_DICT)
		"""打印结果：
		ticket_dict: {
		'ret': '0', 
		'message': '', 
		'skey': '@crypt_3aa5558a_b90fb62556b2573453db1993f5c70510', 
		'wxsid': 'gyqBoDjKXUa9mCZm', 
		'wxuin': '504496135', 
		'pass_ticket': 'y7lOedpMD%2Bq983V1DnQHOAKMMucQqPCKS9psgH8OSrqbLIwUe8tmvaA4ig%2BL0xwn', 
		'isgrayscale': '1'
		}
		"""
		ALL_COOKIE_DICT.update (r2.cookies.get_dict ())
		ret['code'] = 200
		return HttpResponse(json.dumps(ret))    # 将数据传给前端


def wechat_user(request):
	"""3.用户信息界面"""
	# 获取用户信息
	# https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=88828930&lang=zh_CN&pass_ticket
	# =uBfBw5um5Zor97ihMqdFprf4kqjecz8q0VRdevL%252BMg7Ozij4NvnpZCevYQX5jhO0
	# 按照微信网页版的数据提交格式，构造一个字典
	get_user_info_data = {
		'BaseRequest': {
			'DeviceID': "e402310790089148",
			'Sid': TICKET_DICT['wxsid'],
			'Uin': TICKET_DICT['wxuin'],
			'Skey': TICKET_DICT['skey'],
		}
	}
	get_user_info_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=88828930&lang=zh_CN&pass_ticket=" \
	                    + TICKET_DICT['pass_ticket']
	# 发生消息
	r3 = requests.post(
		url=get_user_info_url,
		json=get_user_info_data
	)
	r3.encoding = 'utf-8'
	user_init_dict = json.loads (r3.text)
	# 将用户信息单独保存未全局变量，方便后续使用
	USER_INIT_DICT.update(user_init_dict)
	ALL_COOKIE_DICT.update (r3.cookies.get_dict ())
	# print('*'*20)
	# print('user_init_dict:', user_init_dict)
	# print('*'*20)
	# try:
	# 	for k, v in user_init_dict.items():
	# 		print ('**key**', k, '\n', '**value**', v)
	# except Exception as e:
	# 	print(e)
	for item in user_init_dict['MPSubscribeMsgList']:
		print (item['NickName'])
		for msg in item['MPArticleList']:
			print ('msg.Url:', msg['Url'], 'msg.Title:', msg['Title'])
	return render(request, 'wechat/user.html', {'user_init_dict': user_init_dict})


def contact_ist(request):
	"""4 更多联系人"""

	base_url = "https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?pass_ticket=%s&r=%s&seq=0&skey=%s"
	ctime = time.time()
	url = base_url % (TICKET_DICT['pass_ticket'], ctime, TICKET_DICT['skey'])
	response = requests.get (url=url, cookies=ALL_COOKIE_DICT)
	response.encoding = 'utf-8'
	contact_list_dict = json.loads (response.text)
	for item in contact_list_dict['MemberList']:
		print (item['NickName'], item['UserName'])
	return render(request, 'wechat/contact-list.html', {'contact_list_dict': contact_list_dict})


def send_msg(request):
	"""5 发送消息"""
	to_user = request.GET.get('toUser')
	msg = request.GET.get('msg')

	url = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket=%s' %(TICKET_DICT['pass_ticket'],)
	# 构造数据
	ctime = str(time.time())
	post_dict = {
		'BaseRequest': {
			'DeviceID': "e402310790089148",
			'Sid': TICKET_DICT['wxsid'],
			'Uin': TICKET_DICT['wxuin'],
			'Skey': TICKET_DICT['skey'],
		},
		'Msg': {
			'ClientMsgId': ctime,
			'Content': msg,
			'FromUserName': USER_INIT_DICT['User']['UserName'],
			'LocalID': ctime,
			'ToUserName': to_user.strip(),
			'Type': 1
		},
		'Scene': 0
	}
	requests.post(
		url=url,
	)
	response = requests.post (
		url=url,
		# 将data数据转换为utf-8编码，否则回编程Unicode，中文回出乱码
		data=bytes(json.dumps(post_dict, ensure_ascii=False), encoding='utf-8'))
	print (response.text)
	return HttpResponse ('ok')


def get_msg(request):
	"""获取消息"""
	return render(request, 'wechat/get_mess')
