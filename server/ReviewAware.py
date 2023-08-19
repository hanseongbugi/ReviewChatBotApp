# -*- coding: utf-8 -*-
# 1. json file load
# 2. input query
# 3. 상품 리뷰와 query 간의 cosine similarity 구하기
# 4. 특정 threshold 이상일 때 제품에 점수 추가
# 5. 가장 높은 점수 제품을 출력 OR 제품 별 등수 출력
# 필요한 것 user input, 사용자가 질의한 상품의 category
# user input : 사용자의 문장, 사용자가 원하는 상품명
from sentence_transformers import SentenceTransformer
import time
from urllib import request
import json
import threading
import usingDB
import pandas as pd
from urllib.error import HTTPError
from urllib.error import URLError
import usingDB
import Module.FastTextProcessor as FastTextProcessor
import Module.Encoder as Encoder
from sklearn.metrics.pairwise import cosine_similarity

lock = threading.Lock()
product = {}
type_dict = {"laptop": 0, "desktop": 1, "monitor": 2, "keyboard": 3, "mouse": 4}
name_dict = {}

price_encode = Encoder.encodeProcess("가격")
weight_encode = Encoder.encodeProcess("무게")
attributes_encode = [price_encode,weight_encode]
attribute_dict = {0:"가격", 1:"무게"}


def predictAttribute(input):
    ##################################
    # 추천 의도 판단하기
    # input : 사용자가 입력한 문장
    # 0: 가격 / 1: 무게
    ##################################

    maxCosim = 0
    maxCosim_attributeIdx = -1

    print("#"*50)
    print(input)

    input_words = input.split(" ")
    for input_word in input_words:
        try:
            similar_words = FastTextProcessor.getSimilarWords(input_word)

            for similar_word in similar_words:
                silmilar_word_vec = Encoder.encodeProcess(similar_word[0])
                for idx, attribute_encode in enumerate(attributes_encode):
                    cosim = cosine_similarity([silmilar_word_vec],[attribute_encode])[0][0]

                    if cosim>0.75 and maxCosim<cosim:
                        maxCosim = cosim
                        maxCosim_attributeIdx = idx
        except Exception:
            continue

    if maxCosim_attributeIdx==-1:
        print("최종 판단 불가")
    else:
        print("최종 판단 => "+attribute_dict[maxCosim_attributeIdx])

    print("#"*50)


def queryProductName(productType,product_num):
    #print("productType >>>>>>>", productType)
    type_id = type_dict[productType]
    #print(type_id)
    #print(type_dict[productType])
    conn = usingDB.connectDB()
    cur = conn.cursor()
    sql = "SELECT name FROM product WHERE product_id = "+str(product_num)+" AND type_id = "+str(type_id)
    #print(sql)
    # print(sql,(str(product_num), str(type_id)))
    cur.execute(sql)
    product_name = cur.fetchall()[0][0]
    name_dict[product_num] = product_name
    #print(name_dict)
    cur.close()

def queryProduct(productType, product_num, query_embedding, cosine_score):
    
    try:
        lock.acquire()  # lock
        type_id = type_dict[productType]
        # print(str(product_num))
        lock.release()  # lock 해제
        connection = request.urlopen(
            'http://localhost:8983/solr/'+str(productType)+'/select?fq=product_id%3A'+str(product_num) +
            '&indent=true&q.op=OR&q=*%3A*&useParams=&wt=python'
        )
        response = eval(connection.read())
        
        kValue = response['response']['numFound']
        kValue = round(kValue*0.07)
        if kValue % 2 == 0:
            kValue -= 1
        
        connection = request.urlopen(
            'http://localhost:8983/solr/'+str(productType)+'/select?fq=%7B!frange%20cache%3Dfalse%20l%3D'+str(cosine_score) +
            '%7D%24q&indent=true&q.op=OR&q=%7B!knn%20f%3Dvector%20topK%3D' + str(kValue) + '%7D' + query_embedding +
            '&fq=product_id%3A'+str(product_num)+'&useParams=&wt=python'
            )
            
        response = eval(connection.read())
    except:
        pass
    
    try:
        similar_num = response['response']['numFound']
    except KeyError:
        similar_num = 0

    lock.acquire()  # lock
    product_name = name_dict[product_num]
    product[product_name] = similar_num
    #print(product_name)
    lock.release()  # lock 해제
    

def reviewAware(userId, inputsentence):
    #print("init product")
    product.clear()
    #name_dict = {}

    ### inputsentence 내 추천해줘, 알려줘 이런거 뺄 것  -> nonRecSentence
    nonRecSentence = ''
    #print("Arrive to Review Aware Module")
    model = SentenceTransformer('jhgan/ko-sbert-multitask')
    #print(inputsentence)
    if inputsentence.find("추천해줘") >=0:
        nonRecSentence = inputsentence.replace("추천해줘", "")
    elif inputsentence.find("추천") >=0: 
        nonRecSentence = inputsentence.replace("추천", "")
    #print(nonRecSentence)
    productType = ""
    if nonRecSentence.find('노트북') >= 0 or nonRecSentence.find('놋북') >= 0 or nonRecSentence.find('랩탑') >= 0:
        productType = 'laptop'
    elif nonRecSentence.find('컴퓨터') >= 0 or nonRecSentence.find('pc') >= 0 or nonRecSentence.find('데스크탑') >= 0 or nonRecSentence.find('PC') >= 0 :
        productType = 'desktop'
    elif nonRecSentence.find('모니터') >= 0 :
        productType = 'monitor'
    elif nonRecSentence.find('키보드') >= 0 :
        productType = 'keyboard'
    elif nonRecSentence.find('마우스') >= 0 :
        productType = 'mouse'

    #print("productType is ", productType)
    if productType == '':
        return "추천이 불가능한 상품입니다.", ""

    query = nonRecSentence.strip()
    predictAttribute(query)

    # query = '가벼운 노트북'
    query_embedding = model.encode(query)
    # print(query)
    query_embedding = str(query_embedding.tolist())
    query_embedding = query_embedding.replace('[', '%5B').replace(']', '%5D').replace(',', '%2C').replace(' ', '%20')
    cosine_score = 0.6

    total_start = time.time()  # 시작 시간 저장
    th_list = []
    total_productNum = usingDB.getTotalProductCnt(productType) # productType에 해당하는 상품 개수
    start_productNum = usingDB.getFirstProductId(productType) # productType에 해당하는 상품 시작 product_id
    for product_num in range(total_productNum): # 0 ~ total_productNum-1
        #print("product_num => "+ str(product_num))
        #print("product_num+start_productNum => "+str(product_num+start_productNum))
        queryProductName(productType=productType, product_num=product_num+start_productNum)
    
    #print("Product num!!!", product_num)
    #print("Start Num !! \n", start_productNum)

    print("<<< Solr Query Start >>>")
    for product_num in range(total_productNum): # 0 ~ total_productNum-1
        t = threading.Thread(target=queryProduct, args=(productType, product_num+start_productNum, query_embedding, cosine_score))
        t.start()
        th_list.append(t)
        time.sleep(0.1)
    print("<<< Solr Query End >>>")

    for th in th_list:
        th.join()
    print("run time :", time.time() - total_start)
    sort_product = sorted(product.items(), key=lambda item: item[1], reverse=True)

    recommand_product_1st = sort_product[0] # 추천 1순위 제품
    recommand_product_2nd = sort_product[1] # 추천 2순위 제품
    recommand_product_3rd = sort_product[2] # 추천 3순위 제품

    recommand_1st_name = recommand_product_1st[0] # 추천 1순위 제품 이름
    recommand_1st_score = recommand_product_1st[1] # 추천 1순위 제품 점수
    recommand_2nd_name = recommand_product_2nd[0]
    recommand_2nd_score = recommand_product_2nd[1]
    recommand_3rd_name = recommand_product_3rd[0]
    recommand_3rd_score = recommand_product_3rd[1]

    imageUrls = []
    imageUrls.append(usingDB.getProductImageURL(recommand_1st_name))
    imageUrls.append(usingDB.getProductImageURL(recommand_2nd_name))
    imageUrls.append(usingDB.getProductImageURL(recommand_3rd_name))
    # recname = []
    # recscore = []
    # recname.append(recommand_1st_name)
    # recname.append(recommand_2nd_name)
    # recname.append(recommand_3rd_name)
    # recscore.append(recommand_1st_score)
    # recscore.append(recommand_2nd_score)
    # recscore.append(recommand_3rd_score)


    # print('추천하는 상품은 ', recommand_name, '입니다.')
    # print('점수는', recommand_score, '입니다.')
    return ("'" + inputsentence + "' 와 유사한 상품 리뷰가 많은 순서로 선정한 결과입니다.\n\n"
            + "1위 (" + str(recommand_1st_score) +" 개 리뷰) : %=" + str(recommand_1st_name) + "=%\n"
            + "2위 (" + str(recommand_2nd_score) +" 개 리뷰) : %=" + str(recommand_2nd_name) + "=%\n"
            + "3위 (" + str(recommand_3rd_score) +" 개 리뷰) : %=" + str(recommand_3rd_name) + "=%"), imageUrls