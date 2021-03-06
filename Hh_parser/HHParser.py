import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from Jason2CSV import Converter

chromedriver = '/Users/vikentijzerebov/PycharmProjects/job_boards_parser/selenium_files/chromedriver'
options = webdriver.ChromeOptions()
options.add_argument('headless')  # для открытия headless-браузера
browser = webdriver.Chrome(chromedriver, options=options)


# @todo Придумать как парсить контакты рекрутера - они указаны в некоторых вакансиях и открываются только если
#   ты зарегистрирован как кандидат. То есть тут можно хапнуть бан, поэтому либо придется добавить эмуляцию человека,
#   либо делать левый аккаунт, либо забить болт и просто парсить надеясь на удачу. Чтобы контакты увидеть - надо
#   взаимодействовать с кнопкой "Показать контакты" - это тоже надобно понять как делать.

class VacancyCardMini:
    """
    Объект карточки вакансии, которая отображается в результатах поисковой выдачи HeadHunter,
    тут например https://clck.ru/YeQqw.
    """
    def __init__(self,
                 vacancy_title,
                 vacancy_url,
                 company_title,
                 company_url,
                 vacancy_compensation_from,
                 vacancy_compensation_to,
                 vacancy_currency,
                 ):
        """
        :param vacancy_title: Название вакансии
        :param vacancy_url: Ссылка на вакансию
        :param company_title: Название компании
        :param company_url: Ссылка на компанию
        """
        self.vacancy_currency = vacancy_currency
        self.vacancy_compensation_to = vacancy_compensation_to
        self.vacancy_compensation_from = vacancy_compensation_from
        self.vacancy_title = vacancy_title
        self.vacancy_url = vacancy_url
        self.company_title = company_title
        self.company_url = company_url


class CompanyCardMini:
    """Из каталога компаний - https://hh.ru/employers_company"""
    def __init__(self, company_name, company_url, count_of_opened_vacancies, industry):
        self.industry = industry
        self.count_of_opened_vacancies = count_of_opened_vacancies
        self.company_url = company_url
        self.company_name = company_name


class SearchRequestLink:
    """
    Создает поисковую ссылку для скачивания вакансий или компаний на HeadHunter
    1. Страница поиска вакансий https://hh.ru/search/vacancy
    2. Страница поиска по каталогу компаний https://hh.ru/employers_company
    """
    def __init__(self,
                 area: int = 113,
                 search_field: str = '',
                 clusters: str = '',
                 enable_snippets: str = '',
                 ored_clusters: str = '',
                 schedule: str = '',
                 text: str = '',
                 order_by: str = '',
                 salary: str = '',
                 page: int = 0,
                 only_with_salary: str = '',
                 vacancies_required: str = 'true',
                 label='',
                 company_url='https://hh.ru/employers_company/',
                 special_link: str = ''):
        """
        :param company_url: Ссылка на страницу с компаниями
        :param area: Регион, где искать вакансии или компании. Например 1 - Москва, 2 - Санкт-Петербург, 113 - Россия
        :param label: Можно указывать "label=not_from_agency"
        :param only_with_salary: Показывать только вакансии с зарплатами. = true
        :param search_field: где искать - в названии вакансии ("name"), в описании вакансии (description), компании(company_name), везде
        :param clusters: ХЗ что такое, по дефолту стоит значение true
        :param enable_snippets: ХЗ что такое, по дефолту стоит значение true
        :param ored_clusters: ХЗ что такое, по дефолту стоит значение true
        :param schedule: График работы - если удаленная, то ставим значение remote
        :param text: Текст поискового запроса. Используется как на странице поиска вакансий, так и на странице поиска компаний
        :param order_by: Сортировка поисковой выдачи. Если по зарплате от большего к меньшему, то ставим "salary_desc"
        :param salary: показывать вакансии с зарплатой от указанного значения, например "125000" - покажет соответствующие вакансии
        :param page: Номер поисковой страницы. Начинается как ни странно с 0 страницы. Это ВАЖНО учитывать.
        """
        self.special_link = special_link
        self.vacancies_required = vacancies_required
        self.company_url = company_url
        self.area = area
        self.label = label
        self.only_with_salary = only_with_salary
        self.search_field = search_field
        self.page = page
        self.salary = salary
        self.order_by = order_by
        self.text = text
        self.schedule = schedule
        self.ored_clusters = ored_clusters
        self.enable_snippets = enable_snippets
        self.clusters = clusters

    def make_search_string_for_hh(self) -> str:
        """
        :return: Метод возвращает итоговую ссылку
        """
        url = "https://hh.ru/search/vacancy?"
        search_string_for_hh = url + f'clusters=true&'\
                                     f'area={self.area}'\
                                     f'enable_snippets=true&' \
                                     f'ored_clusters=true&' \
                                     f'text={self.text}&' \
                                     f'order_by={self.order_by}&' \
                                     f'salary={self.salary}&' \
                                     f'schedule={self.schedule}&' \
                                     f'page={self.page}&' \
                                     f'search_field={self.search_field}&' \
                                     f'only_with_salary={self.only_with_salary}&' \
                                     f'label={self.label}'
        # print(search_string_for_hh)
        return search_string_for_hh

    def make_special_search_string_for_hh(self) -> str:
        """ Метод создает ссылку для кипрских компаний"""
        url = "https://cyprus.hh.ru/vacancies/programmist?"
        search_string_for_hh = url + f'page={self.page}'
        # print(search_string_for_hh)
        return search_string_for_hh

    def make_search_string_for_companies(self) -> str:
        """
        1. Метод создает ссылку на HH со списком компаний
        2. По умолчанию ищет по России, если надо регион поменять - изменить параметр area
        3. Если надо взять конкретную область, используй классификатор индустрий по ссылке https://hh.ru/employers_company
        """
        search_string_for_companies = self.company_url + self.search_field + f'?page={self.page}&area={self.area}&vacanciesRequired={self.vacancies_required}'
        return search_string_for_companies

    def make_search_string_for_industries(self) -> str:
        """Метод создает ссылку на HH со списком индустрий https://hh.ru/employers_company"""
        industry_url = self.company_url
        return industry_url


class Salary:
    """
    Сей класс получает значение зарплаты в виде строки и возвращает лист, в котором указана минимальная зарплата,
    максимальная зарплата и валюта. Если какой-то из параметров в вакансии отсутствует - заменяем на "Не указано"
    """
    def __init__(self, salary: str) -> []:
        self.salary = salary

    def salary_parser(self):
        if re.search("от", self.salary):
            low_salary = re.split(' ', self.salary)[1]
            low_salary = re.split("\\u202f", low_salary)[0] + re.split("\\u202f", low_salary)[1]
            high_salary = "Не указано"
            salary_symbol = re.split(' ', self.salary)[2]
        else:
            if re.search("до", self.salary):
                low_salary = "Не указано"
                high_salary = re.split(' ', self.salary)[1]
                high_salary = re.split("\\u202f", high_salary)[0] + re.split("\\u202f", high_salary)[1]
                salary_symbol = re.split(' ', self.salary)[2]
            else:
                if re.search("–", self.salary):
                    low_salary = re.split(" ", self.salary)[0]
                    low_salary = re.split("\\u202f", low_salary)[0] + re.split("\\u202f", low_salary)[1]
                    high_salary = re.split(" ", self.salary)[2]
                    high_salary = re.split("\\u202f", high_salary)[0] + re.split("\\u202f", high_salary)[1]
                    salary_symbol = re.split(' ', self.salary)[3]
                else:
                    low_salary = "не указано"
                    high_salary = "не указано"
                    salary_symbol = "не указано"
        if salary_symbol == 'USD':
            currency = "usd"
        else:
            if salary_symbol == 'USD':
                currency = "usd"
            else:
                if salary_symbol == 'руб.':
                    currency = "rub"
                else:
                    if salary_symbol == 'EUR':
                        currency = "eur"
                    else:
                        currency = "не указано"
        return low_salary, high_salary, salary_symbol, currency


class HhPage:
    def __init__(self, soup: BeautifulSoup):
        self.soup = soup

    def find_number_of_vacancies(self) -> int:
        find_count_string = self.soup.find('h1', class_="bloko-header-section-3").text
        number_of_vacancies = int(re.findall('\\d+', find_count_string)[0])
        return number_of_vacancies

    def number_of_search_pages(self) -> int:
        pagination = self.soup.find_all('a', attrs={'data-qa': 'pager-page'})
        count = int(pagination[-1].text) + 1
        # print(f'count of search pages = {count}')
        return count

    def number_of_search_pages_for_companies(self) -> int:
        pagination = self.soup.find_all('a', attrs={'data-qa': 'pager-page'})
        if len(pagination) == 0:
            count = 0
            # print(f'count of search pages = {count}')
        else:
            count = int(pagination[-1].text)
            # print(f'count of search pages = {count}')
        return count

    def collect_industry_list_from_main_page(self) -> []:
        industry_list = self.soup.find_all(class_='employers-company__item')
        # print(industry_list)
        industries = []
        for industry in industry_list:
            industry_name_rus = industry.text
            industry_url = 'https://spb.hh.ru' + industry.get('href')
            industry_obj = [industry_name_rus, industry_url]
            industries.append(industry_obj)
            print(f'{len(industries)} {industries[len(industries) - 1][0]}')
        return industries

    def collect_sub_industry_list(self) -> []:
        sub_industry_list = self.soup.find_all(class_='employers-sub-industries__item')
        sub_industries = []
        for sub_industry in sub_industry_list:
            sub_industry_name_rus = sub_industry.text
            sub_industry_url = 'https://spb.hh.ru' + sub_industry.get('href')
            sub_industry_obj = [sub_industry_name_rus, sub_industry_url]
            sub_industries.append(sub_industry_obj)
            # print(f'Подраздел индустрии {sub_industry_obj}')
        print(f'количество подразделов индустрии {len(sub_industries)}')
        return sub_industries


class HhClient:
    """vacancy_limit - обрезает компании с количеством вакансий меньше, чем данное значение"""
    def __init__(self, industry, search_request_link: SearchRequestLink, vacancy_limit=0):
        self.industry = industry
        self.vacancy_limit = vacancy_limit
        self.search_request_link = search_request_link

    def get_page_for_cyprus_companies(self) -> HhPage:
        browser.get(f'{self.search_request_link.make_special_search_string_for_hh()}')
        required_html = browser.page_source
        soup = BeautifulSoup(required_html, 'html5lib')
        return HhPage(soup)

    def get_page_for_companies(self) -> HhPage:
        browser.get(f'{self.search_request_link}')
        required_html = browser.page_source
        soup = BeautifulSoup(required_html, 'html5lib')
        return HhPage(soup)

    def get_special_page_for_companies(self) -> HhPage:
        browser.get(f'{self.search_request_link}')
        required_html = browser.page_source
        soup = BeautifulSoup(required_html, 'html5lib')
        return HhPage(soup)

    def get_main_page_for_industries(self) -> HhPage:
        browser.get(f'{self.search_request_link.make_search_string_for_industries()}')
        required_html = browser.page_source
        soup = BeautifulSoup(required_html, 'html5lib')
        return HhPage(soup)

    def get_page_from_industry(self, industry_url) -> HhPage:
        browser.get(industry_url)
        required_html = browser.page_source
        soup = BeautifulSoup(required_html, 'html5lib')
        return HhPage(soup)

    def collect_vacancy_cards_from_page(self) -> [VacancyCardMini]:
        vacancy_cards = self.get_page_for_cyprus_companies().soup.find_all(class_="vacancy-serp-item")
        vacancies = []
        for vacancy_card in vacancy_cards:
            # условие ниже нужно для того, чтобы выявлять вакансии без зарплаты и корректно их обрабатывать
            if len(vacancy_card.find_all('span', class_="bloko-header-section-3 bloko-header-section-3_lite")) > 1:
                salary = Salary(vacancy_card.find_all('span', class_="bloko-header-section-3 bloko-header-section-3_lite")[1].text).salary_parser()
                vac_url = vacancy_card.find('a', class_="bloko-link").get('href')
                vac_url = re.split("\\?", vac_url)[0]
                company_title = vacancy_card.find('a', class_="bloko-link bloko-link_secondary").text
                if re.search("\\xa0", company_title):
                    company_title = re.split("\\xa0", company_title)[0] + " " + re.split("\\xa0", company_title)[1]
                # @todo выяснить, как убрать символ nnbsp. Вот кусок плохого кода:
                #   <div class="vacancy-serp-item__sidebar">
                #   <span data-qa="vacancy-serp__vacancy-compensation"
                #   class="bloko-header-section-3 bloko-header-section-3_lite">
                #   от <!-- -->150 000<!-- --> <!-- -->руб.</span></div>
                vacancy = VacancyCardMini(
                    vacancy_title=vacancy_card.find('a', class_="bloko-link").text,
                    company_title=company_title,
                    company_url="https://hh.ru" + vacancy_card.find('a', class_="bloko-link bloko-link_secondary").get('href'),
                    vacancy_url=vac_url,
                    vacancy_compensation_from=salary[0],
                    vacancy_compensation_to=salary[1],
                    vacancy_currency=salary[3]
                )
                vacancies.append(vacancy)
            else:
                salary = ["Не указано", "Не указано", "Не указано", "Не указано"]
                vac_url = vacancy_card.find('a', class_="bloko-link").get('href')
                vac_url = re.split("\\?", vac_url)[0]
                company_title = vacancy_card.find('a', class_="bloko-link bloko-link_secondary").text
                if re.search("\\xa0", company_title):
                    company_title = re.split("\\xa0", company_title)[0] + " " + re.split("\\xa0", company_title)[1]
                vacancy = VacancyCardMini(
                    vacancy_title=vacancy_card.find('a', class_="bloko-link").text,
                    company_title=company_title,
                    company_url="https://hh.ru" + vacancy_card.find('a', class_="bloko-link bloko-link_secondary").get(
                        'href'),
                    vacancy_url=vac_url,
                    vacancy_compensation_from=salary[0],
                    vacancy_compensation_to=salary[1],
                    vacancy_currency=salary[3]
                )
                vacancies.append(vacancy)
            print(f'{vacancy.vacancy_title}, {vacancy.vacancy_url}, {vacancy.company_title}')
        return vacancies

    def collect_company_cards_from_page(self) -> [CompanyCardMini]:
        company_cards = self.get_page_for_companies().soup.find_all(class_="employers-company__description")
        companies = []
        for company_card in company_cards:
            company_name = company_card.find('a').text
            company_url = 'https://hh.ru' + company_card.find('a').get('href')
            count_of_opened_vacancies = company_card.find('span', class_='employers-company__vacancies-count').text
            company = CompanyCardMini(company_name, company_url, count_of_opened_vacancies)
            if int(count_of_opened_vacancies) >= self.vacancy_limit:
                companies.append(company)
                # print(f'{company.company_name}, {company.company_url}, {company.count_of_opened_vacancies}')
            else:
                # print(f'Меньше {self.vacancy_limit} вакансий, не скачиваем')
                continue
        return companies

    def collect_all_vacancy_cards_from_request(self) -> [VacancyCardMini]:
        search_field = self.search_request_link.search_field
        clusters = self.search_request_link.clusters
        enable_snippets = self.search_request_link.enable_snippets
        ored_clusters = self.search_request_link.ored_clusters
        text = self.search_request_link.text
        order_by = self.search_request_link.order_by
        salary = self.search_request_link.salary
        schedule = self.search_request_link.schedule
        only_with_salary = self.search_request_link.only_with_salary
        label = self.search_request_link.label
        vacancies = []
        for page in range(0, self.get_page_for_cyprus_companies().number_of_search_pages() + 1):
            print(page)
            search_request = SearchRequestLink(search_field=search_field,
                                               clusters=clusters,
                                               enable_snippets=enable_snippets,
                                               ored_clusters=ored_clusters,
                                               text=text,
                                               order_by=order_by,
                                               salary=salary,
                                               page=page,
                                               schedule=schedule,
                                               only_with_salary=only_with_salary,
                                               label=label)
            hh_client = HhClient(search_request_link=search_request)
            collected_data = hh_client.collect_vacancy_cards_from_page()
            vacancies.extend(collected_data)
        print(len(vacancies))
        return vacancies

    def collect_all_company_cards_from_request(self) -> [CompanyCardMini]:
        search_field = self.search_request_link.search_field
        clusters = self.search_request_link.clusters
        enable_snippets = self.search_request_link.enable_snippets
        ored_clusters = self.search_request_link.ored_clusters
        text = self.search_request_link.text
        order_by = self.search_request_link.order_by
        salary = self.search_request_link.salary
        schedule = self.search_request_link.schedule
        only_with_salary = self.search_request_link.only_with_salary
        label = self.search_request_link.label
        area = self.search_request_link.area
        companies = []
        if self.get_page_for_companies().number_of_search_pages_for_companies() == 0:
            print(f'Обрабатываю единственную страницу')
            search_request = SearchRequestLink(search_field=search_field,
                                               clusters=clusters,
                                               enable_snippets=enable_snippets,
                                               ored_clusters=ored_clusters,
                                               text=text,
                                               order_by=order_by,
                                               salary=salary,
                                               page=0,
                                               schedule=schedule,
                                               only_with_salary=only_with_salary,
                                               label=label,
                                               area=area)
            hh_client = HhClient(industry=self.industry, search_request_link=search_request, vacancy_limit=self.vacancy_limit)
            collected_data = hh_client.collect_company_cards_from_page()
            for company in collected_data:
                if company not in companies:
                    companies.extend(collected_data)
        else:
            for page in range(self.get_page_for_companies().number_of_search_pages_for_companies()):
                print(f'Обрабатываю страницу номер {page + 1}')
                search_request = SearchRequestLink(search_field=search_field,
                                                   clusters=clusters,
                                                   enable_snippets=enable_snippets,
                                                   ored_clusters=ored_clusters,
                                                   text=text,
                                                   order_by=order_by,
                                                   salary=salary,
                                                   page=page,
                                                   schedule=schedule,
                                                   only_with_salary=only_with_salary,
                                                   label=label,
                                                   area=area)
                hh_client = HhClient(industry=self.industry, search_request_link=search_request, vacancy_limit=self.vacancy_limit)
                collected_data = hh_client.collect_company_cards_from_page()
                for company in collected_data:
                    if company not in companies:
                        companies.extend(collected_data)
        print(len(companies))
        return companies

    def collect_all_company_cards_from_sub_industry_list(self) -> [CompanyCardMini]:
        search_field = self.search_request_link.search_field
        clusters = self.search_request_link.clusters
        enable_snippets = self.search_request_link.enable_snippets
        ored_clusters = self.search_request_link.ored_clusters
        text = self.search_request_link.text
        order_by = self.search_request_link.order_by
        salary = self.search_request_link.salary
        schedule = self.search_request_link.schedule
        only_with_salary = self.search_request_link.only_with_salary
        label = self.search_request_link.label
        area = self.search_request_link.area
        special_link = self.search_request_link.special_link
        companies = []
        if self.get_special_page_for_companies().number_of_search_pages_for_companies() == 0:
            print(f'Обрабатываю единственную страницу')
            search_request = SearchRequestLink(search_field=search_field,
                                               clusters=clusters,
                                               enable_snippets=enable_snippets,
                                               ored_clusters=ored_clusters,
                                               text=text,
                                               order_by=order_by,
                                               salary=salary,
                                               page=0,
                                               schedule=schedule,
                                               only_with_salary=only_with_salary,
                                               label=label,
                                               area=area,
                                               special_link=special_link)
            hh_client = HhClient(industry=self.industry, search_request_link=search_request, vacancy_limit=self.vacancy_limit)
            collected_data = hh_client.collect_company_cards_from_page()
            for company in collected_data:
                if company not in companies:
                    companies.extend(collected_data)
        else:
            for page in range(self.get_page_for_companies().number_of_search_pages_for_companies()):
                print(f'Обрабатываю страницу номер {page + 1}')
                search_request = SearchRequestLink(search_field=search_field,
                                                   clusters=clusters,
                                                   enable_snippets=enable_snippets,
                                                   ored_clusters=ored_clusters,
                                                   text=text,
                                                   order_by=order_by,
                                                   salary=salary,
                                                   page=page,
                                                   schedule=schedule,
                                                   only_with_salary=only_with_salary,
                                                   label=label,
                                                   area=area)
                hh_client = HhClient(industry=self.industry, search_request_link=search_request, vacancy_limit=self.vacancy_limit)
                collected_data = hh_client.collect_company_cards_from_page()
                for company in collected_data:
                    if company not in companies:
                        companies.extend(collected_data)
        print(len(companies))
        return companies

    def make_json_from_vacancy_search_request(self):
        dict_vacancies_json = []
        collect_all_vacancies = self.collect_all_vacancy_cards_from_request()
        for vacancy in range(1, len(collect_all_vacancies) + 1):
            dict_vacancies_json.append(
                {
                    "Имя вакансии": collect_all_vacancies[vacancy - 1].vacancy_title,
                    "Имя компании": collect_all_vacancies[vacancy - 1].company_title,
                    "Ссылка на компанию": collect_all_vacancies[vacancy - 1].company_url,
                    "Ссылка на вакансию": collect_all_vacancies[vacancy - 1].vacancy_url,
                    "Зарплата от": collect_all_vacancies[vacancy - 1].vacancy_compensation_from,
                    "Зарплата до": collect_all_vacancies[vacancy - 1].vacancy_compensation_to,
                    "Валюта": collect_all_vacancies[vacancy - 1].vacancy_currency
                }
            )
        with open(f"scrapped_data/parsed_hh_vacancies_{current_date}.json", "a", encoding="utf-8") as file:
            json.dump(dict_vacancies_json, file, indent=4, ensure_ascii=False)
        browser.quit()
        return dict_vacancies_json

    def make_json_from_companies_search_request(self):
        dict_companies_json = []
        collect_all_companies = self.collect_all_company_cards_from_request()
        for company in range(1, len(collect_all_companies) + 1):
            dict_companies_json.append(
                {
                    "Имя компании": collect_all_companies[company - 1].company_name,
                    "Ссылка на компанию": collect_all_companies[company - 1].company_url,
                    "Количество открытых вакансий": collect_all_companies[company - 1].count_of_opened_vacancies,
                    "Индустрия":  self.industry
                }
            )
        try:
            with open("/Users/vikentijzerebov/PycharmProjects/Job_Boards_Parser/SavedData/JsonFiles/parsed_hh_companies.json", "r", encoding="utf-8") as f:
                jsn = json.load(f)
        except FileNotFoundError:
            jsn = []

        jsn.extend(dict_companies_json)
        with open("/Users/vikentijzerebov/PycharmProjects/Job_Boards_Parser/SavedData/JsonFiles/parsed_hh_companies.json", 'w', encoding="utf-8") as f:
            json.dump(jsn, f, indent=4, ensure_ascii=False)
        # with open(f"/Users/vikentijzerebov/PycharmProjects/Job_Boards_Parser/SavedData/JsonFiles/parsed_hh_companies.json", "a", encoding="utf-8") as file:
        #     json.dump(dict_companies_json, file, indent=4, ensure_ascii=False)
        json_file_path = f"/Users/vikentijzerebov/PycharmProjects/Job_Boards_Parser/SavedData/JsonFiles/parsed_hh_companies.json"
        # browser.quit()
        return json_file_path


industry_link = SearchRequestLink()
client = HhClient(industry='', search_request_link=industry_link).get_main_page_for_industries()
main_industry_list = client.collect_industry_list_from_main_page()
all_sub_industry_list = []
for industry in main_industry_list:
    client = HhClient(industry='', search_request_link=industry[1]).get_page_from_industry(industry_url=industry[1])
    sub_industry_list = client.collect_sub_industry_list()
    print(industry[0])
    for sub_industry in sub_industry_list:
        print(f'-- {sub_industry[0]}')
    all_sub_industry_list.extend(sub_industry_list)
print(f'Количество всех индустрий равно {len(all_sub_industry_list)}')
for sub in range(len(all_sub_industry_list)):
    print(f'{sub + 1}. {all_sub_industry_list[sub][0]} - {all_sub_industry_list[sub][1]}')
companies = []
for industry1 in range(len(all_sub_industry_list)):
    print(f'Отрабатываю индустрию №{industry1 + 1}. {all_sub_industry_list[industry1][0]}')
    s_i_l = all_sub_industry_list[industry1][1] + "?area=113&vacanciesRequired=true"
    print(s_i_l)
    browser.get(s_i_l)
    required_html = browser.page_source
    soup = BeautifulSoup(required_html, 'html5lib')
    pagination = soup.find_all('a', attrs={'data-qa': 'pager-page'})
    if len(pagination) == 0:
        count = 0
    else:
        count = int(pagination[-1].text)
    if count == 0:
        print('одна страница в мини индустрии')
        company_cards = soup.find_all(class_="employers-company__description")
        for company_card in company_cards:
            company_name = company_card.find('a').text
            company_url = 'https://hh.ru' + company_card.find('a').get('href')
            count_of_opened_vacancies = company_card.find('span', class_='employers-company__vacancies-count').text
            company = CompanyCardMini(company_name, company_url, count_of_opened_vacancies, industry=all_sub_industry_list[industry1][0])
            if int(count_of_opened_vacancies) >= 10:
                if company not in companies:
                    companies.append(company)
                    print(f'{company.company_name}, {company.company_url}, {company.count_of_opened_vacancies}')
            else:
                continue
    else:
        print(f'количество страниц в мини индустрии = {count}')
        for page in range(0, count):
            s_s_i_l = all_sub_industry_list[industry1][1] + f"?page={page}&area=113&vacanciesRequired=true"
            print(s_s_i_l)
            browser.get(s_s_i_l)
            required_html_1 = browser.page_source
            soup_1 = BeautifulSoup(required_html_1, 'html5lib')
            company_cards = soup_1.find_all(class_="employers-company__description")
            for company_card in company_cards:
                company_name = company_card.find('a').text
                company_url = 'https://hh.ru' + company_card.find('a').get('href')
                count_of_opened_vacancies = company_card.find('span', class_='employers-company__vacancies-count').text
                company = CompanyCardMini(company_name, company_url, count_of_opened_vacancies, industry=all_sub_industry_list[industry1][0])
                if int(count_of_opened_vacancies) >= 10:
                    if company not in companies:
                        companies.append(company)
                        print(f'{company.company_name}, {company.company_url}, {company.count_of_opened_vacancies}')
                else:
                    continue
dict_companies_json = []
for company1 in range(len(companies)):
    dict_companies_json.append(
        {
            "Имя компании": companies[company1].company_name,
            "Ссылка на компанию": companies[company1].company_url,
            "Количество открытых вакансий": companies[company1].count_of_opened_vacancies,
            "Индустрия":  companies[company1].industry
        }
    )
with open("/Users/vikentijzerebov/PycharmProjects/Job_Boards_Parser/SavedData/JsonFiles/parsed_hh_companies.json", "a", encoding="utf-8") as f:
    json.dump(dict_companies_json, f, indent=4, ensure_ascii=False)
