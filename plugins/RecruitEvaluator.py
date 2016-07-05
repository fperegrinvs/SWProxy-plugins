from SWProxyVanilla.SWParser.parser import rune_effect_type
import SWPlugin


def get_key(item):
    return item[0]


def averages(lst):
    sorted_list = sorted(lst, key=get_key, reverse=True)
    top_200 = sorted_list[0:200]
    sum_current = sum(n for n,_ in top_200)
    sum_max = sum(n for _,n in top_200)
    list_len = len(top_200) + 0.0

    return sum_current / list_len, sum_max / list_len


class RecruitEvaluator(SWPlugin.SWPlugin):
    six_star_mobs = 0
    six_star_runes = 0
    level_15_runes = 0
    rune_scores = []
    headers = None

    @staticmethod
    def get_sub_score(sub):
        if sub[0] == 0:
            return 0

        rune_type = rune_effect_type(sub[0])
        max = RecruitEvaluator.sub_max_value_map[rune_type] if rune_type in RecruitEvaluator.sub_max_value_map else 0
        return sub[1] / max

    grade_multiplier_map = {
        1: 0.286,
        2: 0.31,
        3: 0.47,
        4: 0.68,
        5: 0.8,
        6: 1
    }

    sub_max_value_map = {
        'HP%': 40.0,
        'ATK%': 40.0,
        'DEF%': 40.0,
        'ACC': 40.0,
        'RES': 40.0,
        'CDmg': 35.0,
        'CRate': 30.0,
        'SPD': 30.0,
        'ATK flat': 14*8.0,
        'HP flat': 344*8.0,
        'DEF flat': 14*8.0,
    }

    @staticmethod
    def rune_efficiency(rune):
        slot = rune['slot_no']

        grade = rune['class']

        main_bonus = 1.5 if slot % 2 == 0 else 0.8

        base_score = main_bonus * RecruitEvaluator.grade_multiplier_map[grade]

        for se in [rune['prefix_eff']] + rune['sec_eff']:
            base_score += RecruitEvaluator.get_sub_score(se)

        level = rune['upgrade_curr']
        subs = 4 - min(level / 3, 4)

        score = (base_score, base_score + (0.2*subs))
        max_score = main_bonus + 1.8

        final_score = (score[0]/max_score, score[1]/max_score)

        return final_score

    def process_csv_row(self, csv_type, data_type, data):
        if csv_type not in ['visit', 'runes']:
            return

        if data_type == 'header':
            RecruitEvaluator.six_star_mobs = 0
            RecruitEvaluator.six_star_runes = 0
            RecruitEvaluator.level_15_runes = 0
            RecruitEvaluator.rune_score = []
            RecruitEvaluator.rune_potential = []

            ids, headers = data

            ids.append('curr_potential')
            ids.append('max_potential')
            headers['curr_potential'] = "Current Potential"
            headers['max_potential'] = "Max Potential"
            RecruitEvaluator.headers = ids
            return
        if data_type == 'rune':
            rune, row = data
            if rune['class'] == 6:
                RecruitEvaluator.six_star_runes += 1
            if rune['upgrade_curr'] == 15:
                RecruitEvaluator.level_15_runes += 1

            eff = self.rune_efficiency(rune)
            RecruitEvaluator.rune_scores.append(eff)

            row['curr_potential'] = "%.2f %%" % (eff[0] * 100)
            row['max_potential'] = "%.2f %%" % (eff[1] * 100)
        elif data_type == 'monster':
            mob, row = data
            if mob['class'] == 6:
                RecruitEvaluator.six_star_mobs += 1
        elif data_type == 'footer':
            headers = RecruitEvaluator.headers
            footer = data
            footer.append({})
            footer.append({
                headers[0]: 'Total 6* mobs',
                headers[1]: 'Total 6* runes',
                headers[2]: 'Total level 15 runes',
                headers[3]: 'Avg. current rune potential',
                headers[4]: 'Avg. max rune potential'})

            avg_curr, avg_max = averages(RecruitEvaluator.rune_scores)

            footer.append({
                headers[0]: RecruitEvaluator.six_star_mobs,
                headers[1]: RecruitEvaluator.six_star_runes,
                headers[2]: RecruitEvaluator.level_15_runes,
                headers[3]: "%.2f %%" % (avg_curr * 100),
                headers[4]: "%.2f %%" % (avg_max * 100)
            })
